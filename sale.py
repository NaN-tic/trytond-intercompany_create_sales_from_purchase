# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta
from trytond.model import fields

__all__ = ['SaleLine']


class SaleLine:
    __metaclass__ = PoolMeta
    __name__ = 'sale.line'
    purchase_line = fields.Many2One('purchase.line', 'Purchase Line')
