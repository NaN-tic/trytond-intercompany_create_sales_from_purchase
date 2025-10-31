# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import ModelView
from trytond.transaction import Transaction


class Purchase(metaclass=PoolMeta):
    __name__ = 'purchase.purchase'

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

        super().process(purchases)

        if to_process:
            companies = Company.search([])
            party_by_companies = dict((c.party, c) for c in companies)
            to_create_by_company = {company: [] for company in companies}

            # create sales grouping by company (user and context from each company)
            for purchase in to_process:
                company = party_by_companies.get(purchase.party)
                if company:
                    to_create_by_company[company] += [purchase]

            for company, purchases in to_create_by_company.items():
                if not purchases:
                    continue


                with Transaction().set_user(0), \
                    Transaction().set_context(company=company.id):
                        to_create = []
                        for purchase in purchases:
                            new_sale = purchase.create_intercompany_sale()
                            if new_sale:
                                to_create.append(new_sale)
                        if to_create:
                            Sale.save(to_create)

    def create_intercompany_sale(self):
        pool = Pool()
        Party = pool.get('party.party')
        Sale = pool.get('sale.sale')

        party = Party(self.company.party.id)

        sale = Sale.search([
            ('reference', '=', self.number),
            ('party', '=', party),
            ], limit=1)
        if sale:
            return

        default_values = Sale.default_get(Sale._fields.keys(),
                with_rec_name=False)

        sale = Sale(**default_values)
        if not sale.warehouse and Sale.warehouse.required:
            sale.warehouse = self.warehouse
        sale.comment = self.comment
        sale.currency = self.currency
        sale.party = party
        sale.on_change_party()
        if Sale.shipment_party.required and not sale.shipment_party:
            if hasattr(self, 'customer') and self.customer:
                sale.shipment_party = self.customer
                sale.shipment_address = self.customer.address_get(type='delivery')
            else:
                sale.shipment_party = party
                sale.shipment_address = party.address_get(type='delivery')
        if not sale.shipment_address:
            sale.shipment_address = party.address_get(type='delivery')
        sale.on_change_shipment_party()
        sale.description = self.description
        sale.payment_term = self.payment_term
        sale.reference = self.number
        sale.sale_date = self.purchase_date
        lines = []
        for line in self.lines:
            if line.type != 'line' or not line.product or not line.product.salable:
                continue
            lines.append(self.create_intercompany_sale_line(sale, line))
        if not lines:
            return
        sale.lines = tuple(lines)
        return sale

    def create_intercompany_sale_line(self, sale, line):
        pool = Pool()
        SaleLine = pool.get('sale.line')
        Product = pool.get('product.product')

        default_values = SaleLine.default_get(SaleLine._fields.keys(),
                with_rec_name=False)

        product = Product(line.product.id)

        sale_line = SaleLine(**default_values)
        sale_line.sale = sale
        sale_line.product = product
        sale_line.unit = line.unit
        sale_line.quantity = line.quantity
        sale_line.on_change_product()
        if sale_line.unit_price is None:
            sale_line.unit_price = line.unit_price
        sale_line.purchase_line = line
        return sale_line
