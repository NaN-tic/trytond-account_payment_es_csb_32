#!/usr/bin/env python
# This file is part of the account_payment_es_csb_32 module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.tests.test_tryton import test_depends
import trytond.tests.test_tryton
import unittest


class AccountPaymentEsCSB32TestCase(unittest.TestCase):
    '''Test Account Payment ES CSB 32 module'''

    def setUp(self):
        trytond.tests.test_tryton.install_module('account_payment_es_csb_32')

    def test0006depends(self):
        'Test depends'
        test_depends()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountPaymentEsCSB32TestCase))
    return suite
