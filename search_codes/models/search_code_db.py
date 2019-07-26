from odoo import models, fields, api
from odoo.osv.expression import get_unaccent_wrapper
import re
class search_code_inherit(models.Model):
    _inherit="res.partner"
    code=fields.Char("Code")
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        self = self.sudo(name_get_uid or self.env.uid)
        if args is None:
            args = []
        if name and operator in ('=', 'ilike', '=ilike', 'like', '=like'):
            self.check_access_rights('read')
            where_query = self._where_calc(args)
            self._apply_ir_rules(where_query, 'read')
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            from_str = from_clause if from_clause else 'res_partner'
            where_str = where_clause and (" WHERE %s AND " % where_clause) or ' WHERE '

            # search on the name of the contacts and of its company
            search_name = name
            if operator in ('ilike', 'like'):
                search_name = '%%%s%%' % name
            if operator in ('=ilike', '=like'):
                operator = operator[1:]

            unaccent = get_unaccent_wrapper(self.env.cr)

            query = """SELECT res_partner.id
                             FROM {from_str}
                          {where} ({email} {operator} {percent}
                               OR {display_name} {operator} {percent}
                               OR {code} {operator} {percent}
                               OR {reference} {operator} {percent}
                               OR {vat} {operator} {percent})
                               -- don't panic, trust postgres bitmap
                         ORDER BY {display_name} {operator} {percent} desc,
                                  {display_name}
                        """.format(from_str=from_str,
                                   where=where_str,
                                   operator=operator,
                                   email=unaccent('res_partner.email'),
                                   code=unaccent('res_partner.code'),
                                   display_name=unaccent('res_partner.display_name'),
                                   reference=unaccent('res_partner.ref'),
                                   percent=unaccent('%s'),
                                   vat=unaccent('res_partner.vat'), )

            where_clause_params += [search_name] * 4  # for email / display_name, reference
            where_clause_params += [re.sub('[^a-zA-Z0-9]+', '', search_name) or None]  # for vat
            where_clause_params += [search_name]  # for order by
            if limit:
                query += ' limit %s'
                where_clause_params.append(limit)
            self.env.cr.execute(query, where_clause_params)
            partner_ids = [row[0] for row in self.env.cr.fetchall()]

            if partner_ids:
                return self.browse(partner_ids).name_get()
            else:
                return []
        return super(search_code_inherit, self)._name_search(name, args, operator=operator, limit=limit, name_get_uid=name_get_uid)
