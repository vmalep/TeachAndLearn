import urllib.request
import urllib.parse
import json
import logging

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)


def _osm_map_src(address):
    """Return an OSM embed iframe src for the given address, or None."""
    if not address:
        return None
    try:
        url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({
            'q': address, 'format': 'json', 'limit': '1',
        })
        req = urllib.request.Request(url, headers={'User-Agent': 'TeachAndLearn/1.0 (odoo-dev)'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        if data:
            lat, lon = float(data[0]['lat']), float(data[0]['lon'])
            m = 0.008
            return (
                f'https://www.openstreetmap.org/export/embed.html'
                f'?bbox={lon-m},{lat-m},{lon+m},{lat+m}&layer=mapnik&marker={lat},{lon}'
            )
    except Exception:
        _logger.debug('OSM geocoding failed for address: %s', address)
    return None


class TeachAndLearnPortal(CustomerPortal):

    @http.route(['/my', '/my/home'], type='http', auth='user', website=True)
    def home(self, **kw):
        profile = request.env['lt.profile'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if profile:
            return request.redirect('/tal/profile')
        return request.redirect('/tal/register')


class TeachAndLearnController(http.Controller):

    def _get_own_profile(self):
        return request.env['lt.profile'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @http.route('/tal/register', auth='public', website=True, sitemap=False)
    def register(self, **kwargs):
        if not request.env.user._is_public():
            profile = self._get_own_profile()
            if profile:
                return request.redirect('/tal/profile')
        return request.render('teach_and_learn.page_register', {
            'error': kwargs.get('error'),
        })

    @http.route('/tal/register/submit', auth='public', website=True,
                methods=['POST'], csrf=True, sitemap=False)
    def register_submit(self, **post):
        name = post.get('name', '').strip()
        email = post.get('email', '').strip()
        password = post.get('password', '').strip()
        is_teacher = bool(post.get('is_teacher'))
        is_student = bool(post.get('is_student'))

        if not name or not email or not password:
            return request.render('teach_and_learn.page_register', {
                'error': 'Please fill in all required fields.',
                'name': name, 'email': email,
            })
        if not is_teacher and not is_student:
            return request.render('teach_and_learn.page_register', {
                'error': 'Please select at least one role (teacher or student).',
                'name': name, 'email': email,
            })

        Users = request.env['res.users'].sudo()
        existing = Users.search([('login', '=', email)], limit=1)
        if existing:
            return request.render('teach_and_learn.page_register', {
                'error': 'An account with this email already exists.',
                'name': name, 'email': email,
            })

        portal_group_id = request.env.ref('base.group_portal').id
        new_user = Users.create({
            'name': name,
            'login': email,
            'email': email,
            'password': password,
            'groups_id': [(6, 0, [portal_group_id])],
        })

        request.env['lt.profile'].sudo().create({
            'user_id': new_user.id,
            'is_teacher': is_teacher,
            'is_student': is_student,
        })

        request.env.cr.commit()  # authenticate() opens its own cursor; commit so it can see the new user
        request.session.authenticate(request.db, {'login': email, 'password': password, 'type': 'password'})
        return request.redirect('/tal/profile')

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    @http.route('/tal/profile', auth='user', website=True, sitemap=False)
    def profile(self, **kwargs):
        profile = self._get_own_profile()
        if not profile:
            # Logged-in user without a profile: show registration form
            return request.render('teach_and_learn.page_register', {
                'error': 'Please complete your registration to continue.',
            })
        languages = request.env['lt.language'].sudo().search([])
        map_address = profile.address or profile.municipality or ''
        map_src = _osm_map_src(map_address)
        return request.render('teach_and_learn.page_profile', {
            'profile': profile,
            'languages': languages,
            'saved': kwargs.get('saved'),
            'error': kwargs.get('error'),
            'map_src': map_src,
        })

    @http.route('/tal/profile/submit', auth='user', website=True,
                methods=['POST'], csrf=True, sitemap=False)
    def profile_submit(self, **post):
        profile = self._get_own_profile()
        if not profile:
            return request.redirect('/tal/register')

        is_teacher = bool(post.get('is_teacher'))
        is_student = bool(post.get('is_student'))

        def to_int_list(key):
            val = post.get(key, '')
            result = []
            for v in (val if isinstance(val, list) else [val]):
                try:
                    result.append(int(v))
                except (ValueError, TypeError):
                    pass
            return result

        vals = {
            'is_teacher': is_teacher,
            'is_student': is_student,
            'bio': post.get('bio', ''),
            'address': post.get('address', ''),
            'municipality': post.get('municipality', ''),
        }
        if is_teacher:
            vals.update({
                'teacher_languages': [(6, 0, to_int_list('teacher_languages'))],
                'native_language_id': int(post['native_language_id']) if post.get('native_language_id') else False,
                'price_per_hour': float(post.get('price_per_hour') or 0),
                'availability': post.get('availability', ''),
            })
        if is_student:
            vals.update({
                'student_languages': [(6, 0, to_int_list('student_languages'))],
                'student_level': post.get('student_level') or False,
                'learning_goals': post.get('learning_goals', ''),
            })

        profile.sudo().write(vals)
        return request.redirect('/tal/profile?saved=1')

    @http.route('/tal/profile/certificates/add', auth='user', website=True,
                methods=['POST'], csrf=True, sitemap=False)
    def certificate_add(self, **post):
        profile = self._get_own_profile()
        if not profile or not profile.is_teacher:
            return request.redirect('/tal/profile')

        cert_name = post.get('cert_name', '').strip()
        if cert_name:
            request.env['lt.certificate'].sudo().create({
                'profile_id': profile.id,
                'name': cert_name,
                'issuing_organization': post.get('issuing_organization', '').strip() or False,
                'date_obtained': post.get('date_obtained') or False,
                'date_expiry': post.get('date_expiry') or False,
                'description': post.get('description', '').strip() or False,
            })
        return request.redirect('/tal/profile?saved=1')

    @http.route('/tal/profile/certificates/<int:cert_id>/delete', auth='user', website=True,
                methods=['POST'], csrf=True, sitemap=False)
    def certificate_delete(self, cert_id, **post):
        profile = self._get_own_profile()
        if not profile:
            return request.redirect('/tal/profile')

        cert = request.env['lt.certificate'].sudo().browse(cert_id)
        if cert.exists() and cert.profile_id.id == profile.id:
            cert.sudo().unlink()
        return request.redirect('/tal/profile?saved=1')

    # ------------------------------------------------------------------
    # Teacher directory
    # ------------------------------------------------------------------

    @http.route('/tal/teachers', auth='user', website=True, sitemap=True)
    def teacher_list(self, **kwargs):
        own_profile = self._get_own_profile()
        if not own_profile:
            return request.redirect('/tal/register')

        domain = [('is_teacher', '=', True), ('teacher_state', '=', 'validated')]
        lang_filter = kwargs.get('language', '').strip()
        location_filter = kwargs.get('location', '').strip()
        max_price = kwargs.get('max_price', '').strip()

        if lang_filter:
            domain.append(('teacher_languages.name', 'ilike', lang_filter))
        if location_filter:
            domain.append(('municipality', 'ilike', location_filter))
        if max_price:
            try:
                domain.append(('price_per_hour', '<=', float(max_price)))
            except ValueError:
                pass

        teachers = request.env['lt.profile'].sudo().search(domain, order='rating desc')
        languages = request.env['lt.language'].sudo().search([])

        return request.render('teach_and_learn.page_teacher_list', {
            'teachers': teachers,
            'languages': languages,
            'lang_filter': lang_filter,
            'location_filter': location_filter,
            'max_price': max_price,
            'own_profile': own_profile,
        })

    @http.route('/tal/teachers/<int:teacher_id>', auth='user', website=True, sitemap=False)
    def teacher_detail(self, teacher_id, **kwargs):
        own_profile = self._get_own_profile()
        if not own_profile:
            return request.redirect('/tal/register')

        teacher = request.env['lt.profile'].sudo().browse(teacher_id)
        if not teacher.exists() or not teacher.is_teacher or teacher.teacher_state != 'validated':
            return request.not_found()

        already_contacted = request.env['lt.contact.request'].sudo().search([
            ('student_id', '=', own_profile.id),
            ('teacher_id', '=', teacher_id),
            ('state', '!=', 'closed'),
        ], limit=1)

        return request.render('teach_and_learn.page_teacher_detail', {
            'teacher': teacher,
            'own_profile': own_profile,
            'already_contacted': already_contacted,
            'sent': kwargs.get('sent'),
        })

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    @http.route('/tal/messages', auth='user', website=True, sitemap=False)
    def messages(self, **kwargs):
        own_profile = self._get_own_profile()
        if not own_profile:
            return request.redirect('/tal/register')

        domain = ['|',
            ('student_id', '=', own_profile.id),
            ('teacher_id', '=', own_profile.id),
        ]
        conversations = request.env['lt.contact.request'].sudo().search(domain)
        return request.render('teach_and_learn.page_messages', {
            'conversations': conversations,
            'own_profile': own_profile,
        })

    @http.route('/tal/messages/<int:request_id>', auth='user', website=True, sitemap=False)
    def message_detail(self, request_id, **kwargs):
        own_profile = self._get_own_profile()
        if not own_profile:
            return request.redirect('/tal/register')

        conv = request.env['lt.contact.request'].sudo().browse(request_id)
        if not conv.exists():
            return request.not_found()
        if conv.student_id.id != own_profile.id and conv.teacher_id.id != own_profile.id:
            return request.not_found()

        messages = conv.message_ids.filtered(
            lambda m: m.message_type in ('comment', 'email') and not m.subtype_id.internal
        ).sorted('date')

        return request.render('teach_and_learn.page_message_detail', {
            'conv': conv,
            'messages': messages,
            'own_profile': own_profile,
            'sent': kwargs.get('sent'),
        })

    @http.route('/tal/messages/<int:request_id>/reply', auth='user', website=True,
                methods=['POST'], csrf=True, sitemap=False)
    def message_reply(self, request_id, **post):
        own_profile = self._get_own_profile()
        if not own_profile:
            return request.redirect('/tal/register')

        conv = request.env['lt.contact.request'].sudo().browse(request_id)
        if not conv.exists():
            return request.not_found()
        if conv.student_id.id != own_profile.id and conv.teacher_id.id != own_profile.id:
            return request.not_found()

        message = post.get('message', '').strip()
        if message:
            conv.message_post(
                body=message,
                author_id=request.env.user.partner_id.id,
                subtype_xmlid='mail.mt_comment',
                message_type='comment',
            )
            if conv.state == 'new':
                conv.write({'state': 'ongoing'})

        return request.redirect(f'/tal/messages/{request_id}?sent=1')

    @http.route('/tal/teachers/<int:teacher_id>/contact', auth='user', website=True,
                methods=['POST'], csrf=True, sitemap=False)
    def contact_teacher(self, teacher_id, **post):
        own_profile = self._get_own_profile()
        if not own_profile or not own_profile.is_student:
            return request.redirect('/tal/profile')

        teacher = request.env['lt.profile'].sudo().browse(teacher_id)
        if not teacher.exists() or not teacher.is_teacher or teacher.teacher_state != 'validated':
            return request.not_found()

        subject = post.get('subject', '').strip()
        message = post.get('message', '').strip()
        if not subject or not message:
            return request.redirect(f'/tal/teachers/{teacher_id}')

        ContactRequest = request.env['lt.contact.request'].sudo()
        contact = ContactRequest.search([
            ('student_id', '=', own_profile.id),
            ('teacher_id', '=', teacher_id),
            ('state', '!=', 'closed'),
        ], limit=1)

        if not contact:
            contact = ContactRequest.create({
                'name': subject,
                'student_id': own_profile.id,
                'teacher_id': teacher_id,
            })

        contact.message_post(
            body=message,
            author_id=request.env.user.partner_id.id,
            subtype_xmlid='mail.mt_comment',
            message_type='comment',
        )

        return request.redirect(f'/tal/teachers/{teacher_id}?sent=1')
