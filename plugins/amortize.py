# Copyright (c) 2017 Cary Kempston
# Source: https://gist.github.com/cdjk/0b8da9e2cc2dee5f3887ab5160970faa
# Modified by Felix Karg <f.karg10@gmail.com> 2020
#   Added: functions 'prepaid', 'electronics', and 'prepaid_transactions'

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import math

from beancount.core import compare
from beancount.core.data import Transaction
from beancount.core.amount import Amount

from datetime import date
from dateutil.relativedelta import relativedelta

__plugins__ = ["amortize", "prepaid", "electronics"]


def amortize(entries, unused_options_map):
    """Repeat a transaction based on metadata.

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
    """
    new_entries = []
    errors = []

    for entry in entries:
        if isinstance(entry, Transaction) and "amortize_months" in entry.meta:
            new_entries.extend(
                prepaid_transactions(entry, None, "amortize", "amortize_months")
            )
        else:
            # Always replicate the existing entries - unless 'amortize_months'
            # is in the metadata
            new_entries.append(entry)

    return new_entries, errors


def prepaid(entries, unused_options_map):
    """ Amortize prepaid expenses. Transforms one transaction in multiple.
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
    """
    new_entries = []
    errors = []

    for entry in entries:
        if isinstance(entry, Transaction) and "prepaid_months" in entry.meta:
            new_entries.extend(
                prepaid_transactions(
                    entry, "Assets:PrepaidExpenses", "prepaid", "prepaid_months"
                )
            )
        else:
            # Always replicate the existing entries - unless 'prepaid_months'
            # is in the metadata
            new_entries.append(entry)

    return new_entries, errors


def electronics(entries, unused_options_map):
    """ Amortize cost of electronics over their lifetime. Transforms one
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
    """
    new_entries = []
    errors = []

    for entry in entries:
        if isinstance(entry, Transaction) and "lifetime_months" in entry.meta:
            new_entries.extend(
                prepaid_transactions(
                    entry, "Assets:Electronics", "electronic", "lifetime_months"
                )
            )
        else:
            # Always replicate the existing entries - unless 'prepaid_months'
            # is in the metadata
            new_entries.append(entry)

    return new_entries, errors


def prepaid_transactions(entry, prepaid_acc, link_pre, period_field):
    if len(entry.postings) != 2:
        raise ValueError("Amortized transactions must have exactly two postings.")

    new_entries = []

    if not (prepaid_acc is None):
        expenses_account = entry.postings[1].account

    periods = entry.meta[period_field]
    link = "{}-{}".format(link_pre, compare.hash_entry(entry)[:12])
    links = set(entry.links).union([link]) if entry.links else set([link])
    amount = abs(entry.postings[0].units.number)
    currency = entry.postings[0].units.currency

    monthly_amounts = split_amount(amount, periods)

    initial_postings = entry.postings

    if not (prepaid_acc is None):
        initial_postings[1] = initial_postings[1]._replace(account=prepaid_acc)

        initial_transaction = Transaction(
            entry.meta,
            entry.date,
            entry.flag,
            "",
            entry.narration,
            entry.tags,
            links,
            initial_postings,
        )

        new_entries.append(initial_transaction)

    new_meta = dict(entry.meta)
    del new_meta[period_field]

    for (n_month, monthly_number) in enumerate(monthly_amounts):
        new_postings = []
        for posting in entry.postings:
            new_monthly_number = monthly_number
            if posting.units.number < 0:
                new_monthly_number = -monthly_number
            new_posting = posting._replace(
                units=Amount(number=new_monthly_number, currency=currency)
            )
            new_postings.append(new_posting)

        if not (prepaid_acc is None):
            new_postings[0] = new_postings[0]._replace(account=prepaid_acc)
            new_postings[1] = new_postings[1]._replace(account=expenses_account)

        new_meta[period_field + "_remaining"] = periods - n_month - 1
        new_entry = entry._replace(meta=dict(new_meta))
        if prepaid_acc is None:
            new_entry = new_entry._replace(links=links)
        else:
            new_entry = new_entry._replace(links=set([link]))
        new_entry = new_entry._replace(postings=new_postings)
        new_entry = new_entry._replace(
            narration="Depreciate: {}".format(entry.narration)
        )
        new_entry = new_entry._replace(
            date=entry.date + relativedelta(months=(1 + n_month))
        )
        # start depreciation one month later
        if new_entry.date <= date.today():
            new_entries.append(new_entry)
        else:
            break
    return new_entries


def split_amount(amount, periods):
    if periods == 1:
        return [amount]
    amount_this_period = amount / periods
    amount_this_period = amount_this_period.quantize(amount)
    return [amount_this_period] + split_amount(amount - amount_this_period, periods - 1)
