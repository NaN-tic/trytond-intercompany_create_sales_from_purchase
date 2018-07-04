# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.

try:
    from trytond.modules.intercompany_create_sales_from_purchase.tests.test_intercompany_create_sales_from_purchase \
        import suite
except ImportError:
    from .test_intercompany_create_sales_from_purchase import suite

__all__ = ['suite']
