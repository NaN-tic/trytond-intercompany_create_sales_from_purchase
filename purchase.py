# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import ModelView, fields
from trytond.transaction import Transaction

__all__ = ['Purchase', 'Company']


class Company:
    __metaclass__ = PoolMeta
    __name__ = 'company.company'

    company_user = fields.Many2One('res.user', 'Company User')


class Purchase:
    __metaclass__ = PoolMeta
    __name__ = 'purchase.purchase'

    @classmethod
    def __setup__(cls):
        super(Purchase, cls).__setup__()
        cls._error_messages.update({
                'empty_address': ('The purchase %s has to be assigned to '
                    'a delivery address or a warehouse with an '
                    'address assigned.')
                })

    @classmethod
    @ModelView.button
    def process(cls, purchases):
        super(Purchase, cls).process(purchases)
        pool = Pool()
        Company = pool.get('company.company')
        Sale = pool.get('sale.sale')
        self_companies = {x.party.id for x in Company.search([])}
        to_create = []
        for purchase in purchases:
            if purchase.party.id not in self_companies:
                continue
            to_create.append(purchase.create_intercompany_sale())
        if to_create:
            Sale.save(to_create)

    def create_intercompany_sale(self):
        pool = Pool()
        Sale = pool.get('sale.sale')
        Company = pool.get('company.company')
        company, = Company.search([('party', '=', self.party.id)])

        purchase_lines = [(l.product.id, l.product.list_price, l.unit,
            l.quantity) for l in self.lines if l.type == 'line']

        with Transaction().set_user(company.company_user.id), \
            Transaction().set_context(
                company=company.id,
                companies=Company.search([]),
                _check_access=False):
            sale = Sale()
            sale.comment = self.comment
            sale.company = company
            sale.party = self.company.party
            sale.on_change_party()
            sale.description = self.description
            sale.payment_term = self.payment_term
            sale.reference = self.number
            sale.sale_date = self.purchase_date
            address = self.delivery_address if hasattr(
                self, 'delivery_address') and \
                self.delivery_address else self.warehouse.address
            if not address:
                self.raise_user_error('empty_address', (self.rec_name,))
            sale.shipment_address = address
            sale.shipment_party = address.party
            if hasattr(sale, 'price_list'):
                sale.price_list = None
            lines = []
            for line in purchase_lines:
                lines.append(self.create_intercompany_sale_line(line))
            if lines:
                sale.lines = tuple(lines)

        return sale

    def create_intercompany_sale_line(self, line):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Product = pool.get('product.product')

        product_id, list_price, unit, quantity = line
        sale_line = SaleLine()
        product = Product(product_id)
        sale_line.product = Product(product_id)
        sale_line.unit_price = list_price
        if not list_price:
            sale_line.unit_price = product.cost_price
        sale_line.unit = unit
        sale_line.quantity = quantity
        sale_line.on_change_product()

        return sale_line
