from odoo import models, fields


class LtContactRequest(models.Model):
    _name = 'lt.contact.request'
    _description = 'Contact Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Subject', required=True)
    student_id = fields.Many2one('lt.profile', string='From (student)', required=True, ondelete='cascade', index=True)
    teacher_id = fields.Many2one('lt.profile', string='To (teacher)', required=True, ondelete='cascade', index=True)
    state = fields.Selection([
        ('new', 'New'),
        ('ongoing', 'Ongoing'),
        ('closed', 'Closed'),
    ], default='new', tracking=True)

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'ongoing'})
