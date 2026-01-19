from odoo import models, fields, api
from odoo.exceptions import UserError

class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'

    trigger_mrp_from_pos = fields.Boolean(
        string="انشاء امر تصنيع تلقائي من pos",
        default=False,
    )