# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ItReportMaintenances(models.AbstractModel):
    _name = 'report.it_parc.report_maintenances'
    _description = 'Rapport Maintenances'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['it.intervention'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'it.intervention',
            'docs': docs,
            'data': data,
        }
