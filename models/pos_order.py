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
        
                # Check stock availability for BoM components
                order._check_components_availability(line, bom)

    def _check_components_availability(self, line, bom):
        """Check if all BoM components have sufficient stock for manufacturing.
        
        :param line: pos.order.line record
        :param bom: mrp.bom record
        :raises UserError: if any component has insufficient stock
        """
        self.ensure_one()
        
        # Get the manufacturing location from the warehouse
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not warehouse:
            raise UserError(_("لم يتم العثور على ستودع لشركة '%(company)s'.", 
                            company=self.company_id.name))
        
        # Get the location where raw materials are stored (stock location)
        location = warehouse.lot_stock_id
        
        # Explode the BoM to get all components and their quantities
        boms, bom_lines = bom.explode(line.product_id, line.qty)
        
        insufficient_components = []
        
        for bom_line, line_data in bom_lines:
            component = bom_line.product_id
            required_qty = line_data['qty']
            
            # Get available quantity in stock location
            available_qty = component.with_context(
                location=location.id
            ).qty_available
            
            if available_qty < required_qty:
                insufficient_components.append({
                    'product': component.display_name,
                    'required': required_qty,
                    'available': available_qty,
                    'shortage': required_qty - available_qty,
                    'uom': bom_line.product_uom_id.name,
                })
        
        if insufficient_components:
            # Build error message with details of all missing components
            error_lines = []
            for comp in insufficient_components:
                error_lines.append(
                    _("  • %(product)s: يتطلب %(required).2f %(uom)s, المتاح %(available).2f %(uom)s (النقص: %(shortage).2f)",
                      product=comp['product'],
                      required=comp['required'],
                      available=comp['available'],
                      shortage=comp['shortage'],
                      uom=comp['uom'])
                )
            
            raise UserError(_(
                "لايمكن تصنيع المنتج '%(product)s'.\n\n"
                "لعدم وجود كمية كافية من\n%(components)s",
                product=line.product_id.display_name,
                components='\n'.join(error_lines)
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
