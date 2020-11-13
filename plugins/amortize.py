# Copyright (c) 2017 Cary Kempston

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

from beancount.core.data import Transaction
from beancount.core.amount import Amount

from datetime import date
from dateutil.relativedelta import relativedelta

__plugins__ = ['amortize']




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
            Assets:Bank:Checking               -600.00 USD
            Assets:Prepaid-Expenses

        2017-06-01 * "Amortize car insurance over six months"
            amortize_months: 3
            Assets:Prepaid-Expenses            -600.00 USD
            Expenses:Insurance:Auto

    into the following transactions over six months:

        2017/06/01 * Pay car insurance
            Assets:Bank:Checking               -600.00 USD
            Assets:Prepaid-Expenses             600.00 USD

        2017/06/01 * Amortize car insurance over six months
            Assets:Prepaid-Expenses            -200.00 USD
            Expenses:Insurance:Auto             200.00 USD

        2017/07/01 * Amortize car insurance over six months
            Assets:Prepaid-Expenses            -200.00 USD
            Expenses:Insurance:Auto             200.00 USD

        2017/08/01 * Amortize car insurance over six months
            Assets:Prepaid-Expenses            -200.00 USD
            Expenses:Insurance:Auto             200.00 USD

    Note that transactions are not included past today's date.  For example,
    if the above transactions are processed on a date of 2017/07/25, the
    transaction dated 2017/08/01 is not included.
    """
    new_entries = []
    errors = []

    for entry in entries:
        if isinstance(entry, Transaction) and 'amortize_months' in entry.meta:
            new_entries.extend(amortize_transaction(entry))
        else:
            # Always replicate the existing entries - unless 'amortize_months'
            # is in the metadata
            new_entries.append(entry)

    return new_entries, errors

def split_amount(amount, periods):
    if periods == 1:
        return [ amount ]
    amount_this_period = amount/periods
    amount_this_period = amount_this_period.quantize(amount)
    return [ amount_this_period ] + split_amount(amount-amount_this_period, periods-1)

def amortize_transaction(entry):

    if len(entry.postings) != 2:
        raise ValueError('Amortized transactions must have exactly two postings.')

    new_entries = []

    original_postings = entry.postings

    periods = entry.meta['amortize_months']

    amount = abs(entry.postings[0].units.number)
    currency = entry.postings[0].units.currency

    monthly_amounts = split_amount(amount, periods)

    for (n_month, monthly_number) in enumerate(monthly_amounts):
        new_postings = []
        for posting in entry.postings:
            new_monthly_number = monthly_number
            if posting.units.number < 0:
                new_monthly_number = -monthly_number
            new_posting = posting._replace(units=Amount(number=new_monthly_number,
                                                        currency=currency))
            new_postings.append(new_posting)

        new_entry = entry._replace(postings=new_postings)
        new_entry = new_entry._replace(date=entry.date + relativedelta(months=(1 + n_month))) # start depreciation one month later
        if new_entry.date <= date.today():
            new_entries.append(new_entry)
    return new_entries
