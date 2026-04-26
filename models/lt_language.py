from odoo import models, fields


class LtLanguage(models.Model):
    _name = 'lt.language'
    _description = 'Language'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'This language already exists.'),
    ]
