# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import purchase

__all__ = ['Purchase']


def register():
    Pool.register(
        purchase.Purchase,
        module='intercompany_create_sales_from_purchase', type_='model')
