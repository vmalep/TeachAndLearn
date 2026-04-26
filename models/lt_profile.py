from odoo import models, fields, api

LEVEL_SELECTION = [
    ('beginner', 'Beginner'),
    ('elementary', 'Elementary'),
    ('intermediate', 'Intermediate'),
    ('upper_intermediate', 'Upper Intermediate'),
    ('advanced', 'Advanced'),
    ('native', 'Native'),
]


class LtProfile(models.Model):
    _name = 'lt.profile'
    _description = 'TeachAndLearn Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', related='user_id.partner_id', store=True)
    name = fields.Char(related='user_id.name', store=True, readonly=False)

    # Role
    is_teacher = fields.Boolean(string='I teach', default=False)
    is_student = fields.Boolean(string='I learn', default=False)

    # Common fields
    bio = fields.Text(string='About me')
    address = fields.Char(string='Address (private)')
    municipality = fields.Char(string='Municipality')

    # Teacher-specific fields
    teacher_languages = fields.Many2many(
        'lt.language', 'lt_profile_teach_lang_rel', 'profile_id', 'language_id',
        string='Languages I teach',
    )
    native_language_id = fields.Many2one('lt.language', string='Native language')
    price_per_hour = fields.Float(string='Price per hour')
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    availability = fields.Text(string='Availability')
    teacher_state = fields.Selection([
        ('draft', 'Pending validation'),
        ('validated', 'Active'),
        ('rejected', 'Rejected'),
    ], string='Teacher status', default='draft', tracking=True)

    # Teacher computed fields
    rating = fields.Float(compute='_compute_rating', store=True)
    review_count = fields.Integer(compute='_compute_rating', store=True)
    review_ids = fields.One2many('lt.review', 'teacher_id', string='Reviews')
    certificate_ids = fields.One2many('lt.certificate', 'profile_id', string='Certificates')

    # Student-specific fields
    student_languages = fields.Many2many(
        'lt.language', 'lt_profile_learn_lang_rel', 'profile_id', 'language_id',
        string='Languages I learn',
    )
    student_level = fields.Selection(LEVEL_SELECTION, string='My level')
    learning_goals = fields.Text(string='My learning goals')

    @api.depends('review_ids.rating')
    def _compute_rating(self):
        for rec in self:
            reviews = rec.review_ids
            rec.review_count = len(reviews)
            rec.rating = sum(reviews.mapped('rating')) / len(reviews) if reviews else 0.0

    def action_validate(self):
        self.write({'teacher_state': 'validated'})

    def action_reject(self):
        self.write({'teacher_state': 'rejected'})

    def action_reset_draft(self):
        self.write({'teacher_state': 'draft'})

    def _is_visible_teacher(self):
        return self.is_teacher and self.teacher_state == 'validated'
