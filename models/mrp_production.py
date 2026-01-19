# -*- coding: utf-8 -*-

from odoo import fields, models


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    pos_order_id = fields.Many2one(
        'pos.order',
        string='POS Order',
        readonly=True,
        index=True,
        help='POS Order that triggered this Manufacturing Order'
    )
