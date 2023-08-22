==========================
Intercompany Sale Scenario
==========================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard, Report, config
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.party_company.tests.test_module import (
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
    >>> address.delivery = True
    >>> address.invoice = True
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> address, = customer.addresses
    >>> address.street = 'St customer'
    >>> address.city = 'City'
    >>> address.delivery = True
    >>> address.invoice = True
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

Create supplier user::

    >>> User = Model.get('res.user')
    >>> Group = Model.get('res.group')
    >>> account_group, = Group.find([('name', '=', 'Account Administration')])
    >>> product_group, = Group.find([('name', '=', 'Product Administration')])
    >>> sale_group, = Group.find([('name', '=', 'Sales Administrator')])
    >>> purchase_group, = Group.find([('name', '=', 'Purchase Administrator')])
    >>> supplier_user = User()
    >>> supplier_user.name = 'supplier'
    >>> supplier_user.login = 'supplier'
    >>> supplier_user.companies.append(company_supplier)
    >>> supplier_user.company = company_supplier
    >>> supplier_user.groups.append(account_group)
    >>> supplier_user.groups.append(product_group)
    >>> supplier_user.groups.append(sale_group)
    >>> supplier_user.groups.append(purchase_group)
    >>> supplier_user.save()

Create customer user::

    >>> account_group, = Group.find([('name', '=', 'Account Administration')])
    >>> product_group, = Group.find([('name', '=', 'Product Administration')])
    >>> sale_group, = Group.find([('name', '=', 'Sales Administrator')])
    >>> purchase_group, = Group.find([('name', '=', 'Purchase Administrator')])
    >>> customer_user = User()
    >>> customer_user.name = 'customer'
    >>> customer_user.login = 'customer'
    >>> customer_user.companies.append(company_customer)
    >>> customer_user.company = company_customer
    >>> customer_user.groups.append(account_group)
    >>> customer_user.groups.append(product_group)
    >>> customer_user.groups.append(sale_group)
    >>> customer_user.groups.append(purchase_group)
    >>> customer_user.save()

    >>> company_supplier.intercompany_user = customer_user
    >>> company_supplier.save()

Create chart of accounts::

    >>> User = Model.get('res.user')

    >>> company_supplier = Company(company_supplier.id)
    >>> company_customer = Company(company_customer.id)

    >>> config.user = supplier_user.id
    >>> config._context = User.get_preferences(True, config.context)
    >>> _ = create_chart(company_supplier)
    >>> accounts_supplier = get_accounts(company_supplier)

    >>> tax_supplier = create_tax(Decimal('.10'), company_supplier)
    >>> tax_supplier.company = company_supplier
    >>> tax_supplier.save()

    >>> config.user = customer_user.id
    >>> config._context = User.get_preferences(True, config.context)
    >>> _ = create_chart(company_customer)
    >>> accounts_customer = get_accounts(company_customer)

    >>> tax_customer = create_tax(Decimal('.10'), company_customer)
    >>> tax_customer.company = company_customer
    >>> tax_customer.save()

Create account categories::

    >>> admin_user, = User.find([('login', '=', 'admin')])
    >>> config._context = User.get_preferences(True, config.context)
    >>> config.user = admin_user.id
    >>> admin_user = User(admin_user.id)
    >>> admin_user.companies.append(company_customer)
    >>> admin_user.company = company_customer
    >>> admin_user.save()
    >>> config._context = User.get_preferences(True, config.context)

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
    >>> template.save()
    >>> product, = template.products
    >>> product.cost_price = Decimal('5')
    >>> product.save()

Set price in supplier company::

    >>> config.user = supplier_user.id
    >>> template, = ProductTemplate.find([])
    >>> template.list_price = Decimal('15')
    >>> template.save()

Create payment term::

    >>> config.user = admin_user.id
    >>> payment_term = create_payment_term()
    >>> payment_term.save()
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
    >>> purchase.click('process')

    >>> purchase_number = purchase.number
    >>> purchase_comment = purchase.comment
    >>> purchase_party = purchase.company.party
    >>> purchase_currency = purchase.currency
    >>> purchase_description = purchase.description
    >>> purchase_payment_term = purchase.payment_term
    >>> purchase_purchase_date = purchase.purchase_date
    >>> purchase_lines = [{
    ...        'product': x.product,
    ...        'quantity': x.quantity,
    ...        'unit': x.unit,
    ...        'unit_price': x.unit_price,
    ...        'cost_price': x.product.cost_price,
    ...        } for x in purchase.lines if x.type == 'line']


    >>> config.user = supplier_user.id
    >>> config._context = User.get_preferences(True, config.context)

    >>> sale, = Sale.find(['reference', '=', purchase_number])
    >>> sale.comment == purchase_comment
    True
    >>> sale.party == purchase_party
    True
    >>> sale.currency == purchase_currency
    True
    >>> sale.description == purchase_description
    True
    >>> sale.payment_term == purchase_payment_term
    True
    >>> sale.sale_date == purchase_purchase_date
    True
    >>> len(sale.lines) == len(purchase_lines)
    True
    >>> for purchase_line, sale_line in zip(purchase_lines, sale.lines):
    ...     print(purchase_line['product'] == sale_line.product,
    ...         purchase_line['quantity'] == sale_line.quantity,
    ...         purchase_line['unit'] == sale_line.unit,
    ...         sale_line.unit_price in (sale_line.product.list_price,
    ...             purchase_line['cost_price']))
    True True True True
    True True True True
