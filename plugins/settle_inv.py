"""Beancount plugin to split transactions which are in transit.

It looks through all Transaction entries with the `settlement-date`-metadata on
one of it's postings and splits those into two transactions.

Example:

    plugin "plugins.settle_inv" "Assets:PayPal"

    2017-04-01 * "" ""
        Assets:SPK              -100.00 EUR
        Expenses:Something
            paypal: 2017-04-03

    ; becomes

    2017-04-01 * "" "Doing some saving transfers" ^settle-43be1c
        Assets:PayPal       -100.00 USD
        Expenses:Something
            settle: 2017-04-03

    2017-04-03 * "" "Settle: Doing some saving transfers" ^settle-43be1c
        Assets:SPK              -100.00 EUR
        Assets:PayPal            100.00 USD
"""

from dateutil.parser import parse

from beancount.core import data, compare

__plugins__ = ['settlement_date']


def settlement_date(entries, options_map, config):
    # config = PayPal account
    errors = []

    for index, entry in enumerate(entries):
        if isinstance(entry, data.Transaction):
            for p_index, posting in enumerate(entry.postings):
                if posting.meta and 'paypal' in posting.meta:
                    postings = entry.postings
                    s_date = posting.meta['paypal']
                    link = 'paypal-{}'.format(compare.hash_entry(entry))
                    original_account = posting.account
                    entry.postings[p_index] = entry.postings[p_index]._replace(account=config)
                    links = set(entry.links).union([link]) \
                            if entry.links else set([link])
                    entries[index] = entry._replace(postings=postings)
                    entries[index] = entry._replace(links=links)

                    new_posting = postings[p_index]
                    new_posting = new_posting._replace(meta=dict())

                    postings = [
                        new_posting,
                        new_posting
                    ]

                    postings[0] = postings[0]._replace(account=original_account)
                    postings[1] = postings[1]._replace(account=config)
                    postings[1] = postings[1]._replace(units=postings[0].units._replace(number=postings[0].units.number*-1))

                    entries.append(data.Transaction(entry.meta, s_date,
                        entry.flag, '', 'Settle: {}'.format(entry.narration),
                        entry.tags, set([link]), postings))

                    break
    return entries, errors
