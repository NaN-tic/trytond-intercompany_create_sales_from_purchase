# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.pool import Pool, PoolMeta
from trytond.model import ModelView, fields
from trytond.transaction import Transaction

__all__ = ['Company', 'Purchase']


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'
    intercompany_user = fields.Many2One('res.user', 'Company User',
        help='User with company rules when create a intercompany sale '
            'from purchases.')


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls._error_messages.update({
                'empty_address': ('The purchase "%s" has to be assigned to '
                    'a delivery address or a warehouse with an '
                    'address assigned.')
                })

    @classmethod
    @ModelView.button
    def process(cls, purchases):
        pool = Pool()
        Company = pool.get('company.company')
        Sale = pool.get('sale.sale')

        to_process = []
        for purchase in purchases:
            if purchase.state == 'confirmed':
                to_process.append(purchase)

        super(Purchase, cls).process(purchases)

        if to_process:
            self_companies = {x.party.id for x in Company.search([])}

            to_create = []
            for purchase in to_process:
                if purchase.party.id not in self_companies:
                    continue
                new_sale = purchase.create_intercompany_sale()
                if new_sale:
                    to_create.append(new_sale)
            if to_create:
                Sale.save(to_create)

    def create_intercompany_sale(self):
        pool = Pool()
        Party = pool.get('party.party')
        Sale = pool.get('sale.sale')
        Company = pool.get('company.company')

        company, = Company.search([('party', '=', self.party.id)], limit=1)
        if not company.intercompany_user:
            return

        with Transaction().set_user(company.intercompany_user.id), \
            Transaction().set_context(
                company=company.id,
                companies=[company.id],
                _check_access=False):
            party = Party(self.company.party.id)
            sale = Sale()
            sale.comment = self.comment
            sale.company = company
            sale.currency = self.currency
            sale.party = party
            sale.on_change_party()
            sale.description = self.description
            sale.payment_term = self.payment_term
            sale.reference = self.number
            sale.sale_date = self.purchase_date
            address = (self.delivery_address
                if hasattr(self, 'delivery_address')
                    and  self.delivery_address
                else self.warehouse.address)
            if not address:
                self.raise_user_error('empty_address', (self.rec_name,))
            sale.shipment_address = address
            sale.shipment_party = address.party
            if hasattr(sale, 'price_list'):
                sale.price_list = None
            lines = []
            for line in self.lines:
                if line.type != 'line':
                    continue
                lines.append(self.create_intercompany_sale_line(sale, line))
            if lines:
                sale.lines = tuple(lines)

        return sale

    def create_intercompany_sale_line(self, sale, line):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Product = pool.get('product.product')

        product = Product(line.product.id)

        sale_line = SaleLine()
        sale_line.sale = sale
        sale_line.product = product
        sale_line.unit = line.unit
        sale_line.quantity = line.quantity
        sale_line.on_change_product()
        if not sale_line.unit_price:
            sale_line.unit_price = line.unit_price
            if hasattr(SaleLine, 'gross_unit_price'):
                sale_line.gross_unit_price = sale_line.unit_price.quantize(
                    Decimal(1) / 10 ** SaleLine.gross_unit_price.digits[1])
        sale_line.purchase_line = line
        return sale_line
