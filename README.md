# beancount-plugins
A collection of plugins I adapted for personal use with
[beancount](https://github.com/beancount/beancount).

## `amortize`

### `amortize`
```
Repeat a transaction based on metadata.

Args:
  entries: A list of directives. We're interested only in the
           Transaction instances.
  unused_options_map: A parser options dict.
Returns:
  A list of entries and a list of errors.

Example use:

This plugin will convert the following transactions

    2017-06-01 * "Pay car insurance"
        Assets:Bank:Checking               -600.00 EUR
        Assets:Prepaid-Expenses

    2017-06-01 * "Amortize car insurance over six months"
        amortize_months: 3
        Assets:Prepaid-Expenses            -600.00 EUR
        Expenses:Insurance:Auto

into the following transactions over six months:

    2017/06/01 * Pay car insurance
        Assets:Bank:Checking               -600.00 EUR
        Assets:Prepaid-Expenses             600.00 EUR

    2017/06/01 * Amortize car insurance over six months
        Assets:Prepaid-Expenses            -200.00 EUR
        Expenses:Insurance:Auto             200.00 EUR

    2017/07/01 * Amortize car insurance over six months
        Assets:Prepaid-Expenses            -200.00 EUR
        Expenses:Insurance:Auto             200.00 EUR

    2017/08/01 * Amortize car insurance over six months
        Assets:Prepaid-Expenses            -200.00 EUR
        Expenses:Insurance:Auto             200.00 EUR

Note that transactions are not included past today's date.  For example,
if the above transactions are processed on a date of 2017/07/25, the
transaction dated 2017/08/01 is not included.
```

### `prepaid`
```
Amortize prepaid expenses. Transforms one transaction in multiple.
Example Use:

    2020-01-01 * "Pay Car Insurance" ^car
      prepaid_months: 6
      Assets:Checking           -600 EUR
      Expenses:Car:Insurance

will be transformed into multiple statements, up until the current day:
    (assuming today is 2020-04-02)

    2020-01-01 * "Car Insurance" ^car ^prepaid-43be1c
      prepaid_months: 6
      Assets:Checking           -600 EUR
      Assets:PrepaidExpenses

    2020-02-01 * "Car Insurance" ^prepaid-43be1c
      prepaid_months_remaining: 5
      Assets:PrepaidExpenses    -100 EUR
      Expenses:Car:Insurance

    2020-03-01 * "Car Insurance" ^prepaid-43be1c
      prepaid_months_remaining: 4
      Assets:PrepaidExpenses    -100 EUR
      Expenses:Car:Insurance

    2020-04-01 * "Car Insurance" ^prepaid-43be1c
      prepaid_months_remaining: 3
      Assets:PrepaidExpenses    -100 EUR
      Expenses:Car:Insurance

Make sure you have an Assets:PrepaidExpenses account.
```

### `electronics`
```
Amortize cost of electronics over their lifetime. Transforms one
transaction in multiple.
Example Use:

    2020-01-01 * "Buy new Phone" ^phone
      lifetime_months: 12
      Assets:Checking           -600 EUR
      Expenses:Phone

will be transformed into multiple statements, up until the current day:
    (assuming today is 2020-04-02)

    2020-01-01 * "Buy new Phone" ^phone ^electronic-43be1c
      lifetime_months: 12
      Assets:Checking           -600 EUR
      Assets:Electronics

    2020-02-01 * "Buy new Phone" ^electronic-43be1c
      lifetime_months_remaining: 11
      Assets:Electronics         -50 EUR
      Expenses:Phone

    2020-03-01 * "Buy new Phone" ^electronic-43be1c
      lifetime_months_remaining: 10
      Assets:Electronics         -50 EUR
      Expenses:Phone

    2020-04-01 * "Buy new Phone" ^electronic-43be1c
      lifetime_months_remaining: 9
      Assets:Electronics         -50 EUR
      Expenses:Phone

Make sure you have an Assets:Electronics account.
```

## `settle`
```
Beancount plugin to split transactions which are in transit.

Source: https://github.com/beancount/fava-plugins/pull/3/files
Author: Dominik Aumayr (github.com/aumayr)

It looks through all Transaction entries with the `settlement-date`-metadata on
one of it's postings and splits those into two transactions.

Example:

    plugin "fava.plugins.settlement_date" "Assets:Savings:Transfer"

    2017-04-01 * "" ""
        Assets:Savings:US       -100.00 USD
        Assets:Savings:JP
            settle: 2017-04-03

    ; becomes

    2017-04-01 * "" "Doing some saving transfers" ^settle-43be1c
        Assets:Savings:US       -100.00 USD
        Assets:Savings:Transfer
            settle: 2017-04-03

    2017-04-03 * "" "Settle: Doing some saving transfers" ^settle-43be1c
        Assets:Savings:Transfer -100.00 USD
        Assets:Savings:JP        100.00 USD
```

## `settle_inv`
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
