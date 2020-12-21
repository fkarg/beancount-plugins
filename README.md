# beancount-plugins
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
---
A collection of plugins I adapted for personal use with
[beancount](https://github.com/beancount/beancount).



```
main.bean
plugins/
├── amortize.py
│   ├── amortize (function)
│   ├── prepaid (function)
│   └── electronics (function)
├── settle_inv.py
│   └── settle_inv (function)
└── settle.py
    └── settle (function)
```

The functionality is split across three plugins and five functions, additional
auxiliary functions used by multiple plugin-functions exist.

I recommend activating `settle`-plugins prior to `amortize` for everything to
function properly. As in; my `main.bean` looks like this:

```
...

* Plugins
option "insert_pythonpath" "True" ; for importing plugins
plugin "plugins.settle" "Assets:Extern:Transit"    ; Transactions in transit
plugin "plugins.settle_inv" "Assets:PayPal"        ; settle PayPal payments later
plugin "plugins.amortize"   ; amortizing transactions over longer durations

* Includes
include "transactions/all.bean"   ; take in all transactions
...
```


## Plugin `amortize`

### Function `amortize`
    Repeat a transaction based on metadata.

    Args:
      entries: A list of directives. We're interested only in the
               Transaction instances.
      unused_options_map: A parser options dict.
    Returns:
      A list of entries and a list of errors.

    Example use:

    This plugin will convert the following transactions

        2017-06-01 * "Car Insurance"
            Assets:Bank:Checking               -600.00 EUR
            Assets:Prepaid-Expenses

        2017-06-01 * "Car Insurance"
            amortize_months: 3
            Assets:Prepaid-Expenses            -600.00 EUR
            Expenses:Insurance:Auto

    into the following transactions over three months:

        2017/06/01 * Car Insurance
            Assets:Bank:Checking               -600.00 EUR
            Assets:Prepaid-Expenses             600.00 EUR

        2017/07/01 * Depreciate: Car Insurance ^amortize-416e2f90
            amortize_months_remaining: 2
            Assets:Prepaid-Expenses            -200.00 EUR
            Expenses:Insurance:Auto             200.00 EUR

        2017/08/01 * Depreciate: Car Insurance ^amortize-416e2f90
            amortize_months_remaining: 1
            Assets:Prepaid-Expenses            -200.00 EUR
            Expenses:Insurance:Auto             200.00 EUR

        2017/09/01 * Depreciate: Car Insurance ^amortize-416e2f90
            amortize_months_remaining: 0
            Assets:Prepaid-Expenses            -200.00 EUR
            Expenses:Insurance:Auto             200.00 EUR

    Note that transactions are not included past today's date. For example,
    if the above transactions are processed on 2017/07/25, the transactions
    dated 2017/08/01 and 2017/09/01 are not included. By default, the first
    transaction happens one month after the amortizing statement. This can be
    changed to one month after a date given in 'arrived' or 'starting'.
    Example:

        2017-06-01 * "Car Insurance"
            amortize_months: 3
            starting: 2017-09-01
            Assets:Prepaid-Expenses            -600.00 EUR
            Expenses:Insurance:Auto

    In this case, the first transaction will be on 2017-10-01.


### Function `prepaid`
    Amortize prepaid expenses. Transfers full amount to
    'Assets:PrepaidExpenses' first and amortizes amount over timeframe.
    Example Use:

        2020-01-01 * "Car Insurance" ^car
          prepaid_months: 6
          Assets:Checking           -600 EUR
          Expenses:Car:Insurance

    will be transformed into multiple transactions, up until the current day:
        (assuming today is 2020-04-02)

        2020-01-01 * "Car Insurance" ^car ^prepaid-43be1c
          prepaid_months: 6
          Assets:Checking           -600 EUR
          Assets:PrepaidExpenses

        2020-02-01 * "Depreciate: Car Insurance" ^prepaid-43be1c
          prepaid_months_remaining: 5
          Assets:PrepaidExpenses    -100 EUR
          Expenses:Car:Insurance

        2020-03-01 * "Depreciate: Car Insurance" ^prepaid-43be1c
          prepaid_months_remaining: 4
          Assets:PrepaidExpenses    -100 EUR
          Expenses:Car:Insurance

        2020-04-01 * "Depreciate: Car Insurance" ^prepaid-43be1c
          prepaid_months_remaining: 3
          Assets:PrepaidExpenses    -100 EUR
          Expenses:Car:Insurance

    Make sure you have an Assets:PrepaidExpenses account. Field 'starting' can
    be used to specify an earlier/later initial date, one month after which
    amortization starts.


### Function `electronics`
    Amortize cost of electronics over their lifetime. Transforms one
    transaction in multiple.
    Example Use:

        2020-01-01 * "New Phone" ^phone
          lifetime_months: 12
          Assets:Checking           -600 EUR
          Expenses:Phone

    will be transformed into multiple statements, up until the current day:
        (assuming today is 2020-04-02)

        2020-01-01 * "New Phone" ^phone ^electronic-43be1c
          lifetime_months: 12
          Assets:Checking           -600 EUR
          Assets:Electronics

        2020-02-01 * "Depreciate: New Phone" ^electronic-43be1c
          lifetime_months_remaining: 11
          Assets:Electronics         -50 EUR
          Expenses:Phone

        2020-03-01 * "Depreciate: New Phone" ^electronic-43be1c
          lifetime_months_remaining: 10
          Assets:Electronics         -50 EUR
          Expenses:Phone

        2020-04-01 * "Depreciate: New Phone" ^electronic-43be1c
          lifetime_months_remaining: 9
          Assets:Electronics         -50 EUR
          Expenses:Phone

    Make sure you have an Assets:Electronics account. If 'arrived' is
    specified, depreciation starts one month after that. Example:
          (assuming that today is 2020-04-02)

        2020-01-01 * "New Phone" ^phone ^electronic-56f2254e8f44
          arrived: 2020-02-12
          lifetime_months: 12
          Assets:Checking           -600 EUR
          Assets:Electronics

        2020-03-12 * "Depreciate: New Phone" ^electronic-56f2254e8f44
          lifetime_months_remaining: 11
          Assets:Electronics         -50 EUR
          Expenses:Phone



## Plugin `settle`
```
Beancount plugin to split transactions which are in transit.

Source: https://github.com/beancount/fava-plugins/pull/3/files
Author: Dominik Aumayr (github.com/aumayr)

It looks through all Transaction entries with the `settlement-date`-metadata on
one of it's postings and splits those into two transactions.

Example:

    plugin "fava.plugins.settlement_date" "Assets:Savings:Transfer"

    2017-04-01 * "Doing some saving transfers"
        Assets:Savings:US       -100.00 USD
        Assets:Savings:JP
            settle: 2017-04-03

    ; becomes

    2017-04-01 * "Doing some saving transfers" ^settle-43be1c
        Assets:Savings:US       -100.00 USD
        Assets:Savings:Transfer
            settle: 2017-04-03

    2017-04-03 * "Settle: Doing some saving transfers" ^settle-43be1c
        Assets:Savings:Transfer -100.00 USD
        Assets:Savings:JP        100.00 USD


    ; also; in case of settling negative parts later:
    2017-04-01 * "Doing some saving transfers"
        Assets:Savings:US               -100.00 USD
            settle: 2017-04-03
        Assets:Savings:JP

    ; becomes

    2017-04-01 * "Doing some saving transfers" ^settle-43be1c
        Liabilities:AccountsPayable     -100.00 USD
            settle: 2017-04-03
        Assets:Savings:JP                100.00 USD

    2017-04-03 * "Settle: Doing some saving transfers" ^settle-43be1c
        Assets:Savings:US               -100.00 USD
        Liabilities:AccoutsPayable       100.00 USD

    ; make sure you have a `Liabilities:AccoutsPayable` account for that.


    ; can also be combined, or used multiple times in one transaction:
    2017-04-01 * "Bought some gifts, and stuff for someone else"
        Assets:Checkings            -100 USD
            settle: 2017-04-03
        Assets:Checkings            -120 USD
            settle: 2017-04-05
        Assets:Voucher               -20 USD
        Expenses:Gifts                70 USD
        Assets:Checkings             170 USD
            settle: 2017-04-20

    ; will be split apart as expected, with a different link for each settlement.
```

## Plugin `settle_inv`
```
Beancount plugin to split transactions which are in transit.

Source: https://github.com/beancount/fava-plugins/pull/3/files
Author: Dominik Aumayr (github.com/aumayr)
Modified by Felix Karg (github.com/fkarg) 2020

It looks through all Transaction entries with the `paypal`-metadata on
one of it's postings and splits those into two transactions.

Example:

    plugin "plugins.settle_inv" "Assets:PayPal"

    2017-04-03 * "Paid for something with PayPal" #tag ^link
        Assets:Checkings        -100.00 EUR
            paypal: 2017-04-01
        Expenses:Something

    ; becomes

    2017-04-01 * "Paid for something with PayPal" #tag ^link ^settle-43be1c
        Assets:PayPal           -100.00 EUR
        Expenses:Something

    2017-04-03 * "Settle: Paid for something with PayPal" #tag ^link ^settle-43be1c
        Assets:Checkings        -100.00 EUR
        Assets:PayPal            100.00 EUR

```
