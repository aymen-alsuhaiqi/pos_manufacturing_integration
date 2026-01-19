# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    mrp_production_ids = fields.One2many(
        'mrp.production',
        'pos_order_id',
        string='Manufacturing Orders',
        readonly=True
    )

    def _process_saved_order(self, draft):
        """Extended to create Manufacturing Orders after payment."""
        res = super()._process_saved_order(draft)
        if not draft and self.state != 'cancel':
            self._validate_pos_manufacturing_products()
            self._create_manufacturing_orders()
        return res

    def _validate_pos_manufacturing_products(self):
        """Validate all POS manufacturing products have valid BoMs and sufficient stock before payment."""
        MrpBom = self.env['mrp.bom']
        for order in self:
            for line in order.lines.filtered(
                lambda l: l.product_id.product_tmpl_id.trigger_mrp_from_pos
                and l.qty > 0  # Only check for positive quantities (not refunds)
            ):
                product = line.product_id
                bom = MrpBom._bom_find(product, bom_type='normal').get(product)
                if not bom:
                    raise UserError(_(
                        "Cannot process order: Product '%(product)s' requires "
                        "manufacturing but has no valid Bill of Materials.",
                        product=product.display_name
                    ))
                
    def _create_manufacturing_orders(self):
        """Create Manufacturing Orders for products configured for POS manufacturing."""
        MrpProduction = self.env['mrp.production']
        MrpBom = self.env['mrp.bom']

        for order in self:
            for line in order.lines.filtered(
                lambda l: l.product_id.product_tmpl_id.trigger_mrp_from_pos
                and l.qty > 0  # Only create MO for positive quantities (not refunds)
            ):
                product = line.product_id
                bom = MrpBom._bom_find(product, bom_type='normal').get(product)

                if not bom:
                    continue  # Skip if no BoM (validation should catch this upstream)

                mo_vals = order._prepare_manufacturing_order_vals(line, bom)
                mo = MrpProduction.create(mo_vals)
                mo.action_confirm()

    def _prepare_manufacturing_order_vals(self, line, bom):
        """Prepare values for Manufacturing Order creation.
        
        Design Decision: MO is created in draft and then confirmed to properly
        reserve raw materials. The origin field links back to the POS order
        for traceability.
        
        :param line: pos.order.line record
        :param bom: mrp.bom record
        :return: dict of values for mrp.production.create()
        """
        self.ensure_one()
        
        # Get the picking type for manufacturing from the company's warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        
        return {
            'product_id': line.product_id.id,
            'product_qty': line.qty,
            'bom_id': bom.id,
            'product_uom_id': line.product_uom_id.id if line.product_uom_id else line.product_id.uom_id.id,
            'company_id': self.company_id.id,
            'origin': _("POS: %(order_name)s", order_name=self.name),
            'pos_order_id': self.id,
            'picking_type_id': picking_type.id if picking_type else False,
        }
