from odoo import models, fields


class LtCertificate(models.Model):
    _name = 'lt.certificate'
    _description = 'Teacher Certificate'
    _order = 'date_obtained desc'

    profile_id = fields.Many2one('lt.profile', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Certificate Name', required=True)
    issuing_organization = fields.Char(string='Issuing Organization')
    date_obtained = fields.Date(string='Date Obtained')
    date_expiry = fields.Date(string='Expiry Date')
    description = fields.Text(string='Description')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'lt_certificate_attachment_rel', 'certificate_id', 'attachment_id',
        string='Documents',
    )
