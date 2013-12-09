## coding: utf-8
# This file is part of account_payment_es_csb_32 module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
import logging
try:
    from retrofix import Record, write, c32
except ImportError:
    message = ('Unable to import retrofix library.\n'
               'Please install it before install this module.')
    logging.getLogger('account_payment_es_csb_32').error(message)
    raise Exception(message)

__all__ = [
    'Journal',
    'Group',
    ]
__metaclass__ = PoolMeta


class Journal:
    __name__ = 'account.payment.journal'
    csb_32_grantor = fields.Char('Grantor', states={
            'required': Eval('process_method') == 'csb32',
            })

    @classmethod
    def __setup__(cls):
        super(Journal, cls).__setup__()
        if ('csb32', 'CSB 32') not in cls.process_method.selection:
            cls.process_method.selection.extend([
                    ('csb32', 'CSB 32'),
                    ])


class Group:
    __name__ = 'account.payment.group'

    def set_default_csb32_payment_values(self):
        values = self.set_default_payment_values()
        values['grantor_identifier'] = values['payment_journal'].csb_32_grantor
        if not values['province'] or not values['city']:
            self.raise_user_error('configuration_error',
                error_description='company_without_complete_address',
                error_description_args=(values['name'],))
        values['bank_account'] = values['bank_account'].numbers[0].number
        values['record_count'] = 0
        values['payment_count'] = 0
        values['document_number'] = 0
        for receipt in values['receipts']:
            if not receipt['vat_number']:
                self.raise_user_error('configuration_error',
                    error_description='party_without_vat_number',
                    error_description_args=(receipt['party'].name,))

            if not receipt['address']:
                self.raise_user_error('configuration_error',
                    error_description='party_without_address',
                    error_description_args=(receipt['party'].name,))

            if not receipt['province']:
                self.raise_user_error('configuration_error',
                    error_description='party_without_province',
                    error_description_args=(receipt['party'].name,))
        return values

    @classmethod
    def process_csb32(cls, group):

        def set_file_header_record():
            record = Record(c32.FILE_HEADER_RECORD)
            record.record_code = '02'
            record.data_code = '65'
            record.file_date = values['creation_date']
            record.number = values['number']
            record.bank_code = values['bank_account'][0:4]
            record.bank_office = values['bank_account'][4:8]
            return write([record])

        def set_order_header_record():
            record = Record(c32.ORDER_HEADER_RECORD)
            record.record_code = '11'
            record.data_code = '65'
            record.file_date = values['creation_date']
            record.order_number = '0001'
            record.grantor_identifier = values['grantor_identifier']
            record.truncated = '1'
            record.account_payment_1 = values['bank_account']
            record.account_payment_2 = values['bank_account']
            record.account_payment_3 = values['bank_account']
            return write([record])

        def set_individual_1_record():
            record = Record(c32.INDIVIDUAL_1_RECORD)
            record.record_code = '25'
            record.data_code = '65'
            record.document_number = str(values['document_number']).zfill(15)
            record.file_date = values['creation_date']
            record.order_number = '0001'
            record.province_code = values['province']
            record.ine = values['ine_code']
            record.city = values['city']
            record.amount = receipt['amount']
            record.date_due = receipt['maturity_date']
            return write([record])

        def set_individual_2_record():
            record = Record(c32.INDIVIDUAL_2_RECORD)
            record.record_code = '26'
            record.data_code = '65'
            record.document_number = str(values['document_number']).zfill(15)
            # 1: 'bill of exchange', 2: 'receipt', 3: 'promissory note'
            record.document_type = '2'
            # Mandatory for 'bill of exchange' and 'promissory note'
            record.send_date = values['creation_date']
            # Code of accepted: 1: accepted, 2: not accepted
            record.accept_code = '2'
            # 0: No fees, 1: Expenses, 9: Order expressly notarial protest
            record.expenses_clause = '0'
            record.account = receipt['bank_account'].numbers[0].number
            record.sender_name = values['party'].name
            record.receiver_name = receipt['party'].name
            record.additional_information = ''
            return write([record])

        def set_individual_3_record():
            record = Record(c32.INDIVIDUAL_3_RECORD)
            record.record_code = '27'
            record.data_code = '65'
            record.document_number = str(values['document_number']).zfill(15)
            record.receiver_address = receipt['address'].street
            record.receiver_zip = receipt['address'].zip
            record.receiver_city = receipt['address'].city
            record.receiver_province_code = receipt['province']
            record.receiver_ine = '0000000'
            record.receiver_nif = receipt['vat_number']
            return write([record])

        def set_order_footer_record():
            record = Record(c32.ORDER_FOOTER_RECORD)
            record.record_code = '71'
            record.data_code = '65'
            record.file_date = values['creation_date']
            record.order_number = '0001'
            record.amount = values['amount']
            record.record_count = str(values['record_count'])
            record.payment_count = str(values['payment_count'])
            return write([record])

        def set_file_footer_record():
            record = Record(c32.FILE_FOOTER_RECORD)
            record.record_code = '98'
            record.data_code = '65'
            record.amount = values['amount']
            record.order_count = '00001'
            record.record_count = str(values['record_count'])
            record.payment_count = str(values['payment_count'])
            return write([record])

        values = Group.set_default_csb32_payment_values(group)
        text = set_file_header_record()
        values['record_count'] += 1
        text += set_order_header_record()
        values['record_count'] += 1
        for receipt in values['receipts']:
            values['document_number'] += 1
            text += set_individual_1_record()
            values['record_count'] += 1
            text += set_individual_2_record()
            values['record_count'] += 1
            text += set_individual_3_record()
            values['record_count'] += 1
            values['payment_count'] += 1
        text += set_order_footer_record()
        values['record_count'] += 2
        text += set_file_footer_record()
        group.attach_file(text)
