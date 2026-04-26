from odoo import models, fields, api
from odoo.exceptions import ValidationError


class LtReview(models.Model):
    _name = 'lt.review'
    _description = 'Teacher Review'
    _order = 'date desc'

    teacher_id = fields.Many2one('lt.profile', required=True, ondelete='cascade', index=True)
    student_id = fields.Many2one('lt.profile', required=True, ondelete='cascade', index=True)
    rating = fields.Integer(required=True, default=5)
    comment = fields.Text()
    date = fields.Date(default=fields.Date.today, readonly=True)

    _sql_constraints = [
        ('one_review_per_pair', 'UNIQUE(teacher_id, student_id)',
         'You have already reviewed this teacher.'),
    ]

    @api.constrains('rating')
    def _check_rating(self):
        for rec in self:
            if not 1 <= rec.rating <= 5:
                raise ValidationError('Rating must be between 1 and 5.')

    @api.constrains('teacher_id', 'student_id')
    def _check_different_profiles(self):
        for rec in self:
            if rec.teacher_id == rec.student_id:
                raise ValidationError('You cannot review yourself.')
            if not rec.teacher_id.is_teacher:
                raise ValidationError('The reviewed profile must be a teacher.')
            if not rec.student_id.is_student:
                raise ValidationError('Only students can write reviews.')
