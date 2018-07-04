=================
Intercompany Sale Scenario
=================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard, Report, config
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.party_company.tests.test_party_company import (
    ...     set_company)
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences, create_payment_term
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> today = datetime.date.today()

Install intercompany_create_sales_from_purchase::

    >>> config = activate_modules('intercompany_create_sales_from_purchase')

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> address, = supplier.addresses
    >>> address.street = 'St supplier'
    >>> address.city = 'City'
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> address, = customer.addresses
    >>> address.street = 'St customer'
    >>> address.city = 'City'
    >>> customer.save()

Create companies::

    >>> Company = Model.get('company.company')
    >>> company_supplier = Company()
    >>> company_supplier.party = supplier
    >>> company_supplier.currency = get_currency()
    >>> company_supplier.save()
    >>> company_customer = Company()
    >>> company_customer.party = customer
    >>> company_customer.currency = get_currency()
    >>> company_customer.save()
    >>> companies = [company_supplier, company_customer]

Create chart of accounts::
    >>> User = Model.get('res.user')
    >>> current_user, = User.find([('login', '=', 'admin')])
    >>> current_user.main_company = company_supplier
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> _ = create_chart(company_supplier)
    >>> accounts_supplier = get_accounts(company_supplier)
    >>> current_user.main_company = company_customer
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> _ = create_chart(company_customer)
    >>> accounts_customer = get_accounts(company_customer)

Create tax::

    >>> current_user.main_company = company_supplier
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> tax_supplier = create_tax(Decimal('.10'), company_supplier)
    >>> tax_supplier.save()
    >>> current_user.main_company = company_customer
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> tax_customer = create_tax(Decimal('.10'), company_customer)
    >>> tax_customer.save()


Create account categories::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category_customer = ProductCategory(name="Account Category")
    >>> account_category_customer.accounting = True
    >>> account_category_customer.account_expense = accounts_customer['expense']
    >>> account_category_customer.account_revenue = accounts_customer['revenue']
    >>> account_category_customer.save()

Create product with differents list_price for companies::
    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'goods'
    >>> template.purchasable = True
    >>> template.salable = True
    >>> template.list_price = Decimal('10')
    >>> template.cost_price_method = 'fixed'
    >>> template.account_category = account_category_customer

    >>> # TODO: Delete the next 2 lines in 5.0 version
    >>> template.account_expense = template.account_category.account_expense
    >>> template.account_revenue = template.account_category.account_revenue

    >>> template.save()
    >>> product, = template.products
    >>> product.cost_price = Decimal('5')
    >>> product.save()
    >>> current_user.main_company = company_supplier
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> template, = ProductTemplate.find([])
    >>> template.list_price = Decimal('15')
    >>> template.save()

Create payment term::

    >>> payment_term = create_payment_term()
    >>> payment_term.save()
    >>> current_user.main_company = company_customer
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> payment_term = create_payment_term()
    >>> payment_term.save()


Purchase 5 products::

    >>> Purchase = Model.get('purchase.purchase')
    >>> PurchaseLine = Model.get('purchase.line')
    >>> Sale = Model.get('sale.sale')
    >>> purchase = Purchase()
    >>> purchase.party = supplier
    >>> purchase.payment_term = payment_term
    >>> purchase.invoice_method = 'order'
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 2.0
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.type = 'comment'
    >>> purchase_line.description = 'Comment'
    >>> purchase_line = PurchaseLine()
    >>> purchase.lines.append(purchase_line)
    >>> purchase_line.product = product
    >>> purchase_line.quantity = 3.0
    >>> purchase.click('quote')
    >>> purchase.click('confirm')
    >>> purchase.click('process') # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ...
    >>> purchase.warehouse.address, = customer.addresses
    >>> purchase.warehouse.save()
    >>> purchase.click('process')
    >>> purchase_number = purchase.number
    >>> current_user.main_company = company_supplier
    >>> current_user.save()
    >>> config._context = User.get_preferences(True, config.context)
    >>> sale, = Sale.find(['reference', '=', purchase_number])
    >>> sale.comment == purchase.comment
    True
    >>> sale.party == purchase.company.party
    True
    >>> sale.currency == purchase.currency
    True
    >>> sale.currency_digits == purchase.currency_digits
    True
    >>> sale.description == purchase.description
    True
    >>> sale.payment_term == purchase.payment_term
    True
    >>> sale.sale_date == purchase.purchase_date
    True
    >>> purchase_lines_type_line = [x for x in purchase.lines if x.type == 'line']
    >>> len(sale.lines) == len(purchase_lines_type_line)
    True
    >>> for line in zip(purchase_lines_type_line, sale.lines):
    ...     print (line[0].product == line[1].product,
    ...         line[0].quantity == line[1].quantity,
    ...         line[0].unit == line[1].unit,
    ...         line[1].unit_price in (line[1].product.list_price,
    ...             line[0].product.cost_price))
    (True, True, True, True)
    (True, True, True, True)
