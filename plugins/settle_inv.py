"""Beancount plugin to split transactions which are in transit.

It looks through all Transaction entries with the `settlement-date`-metadata on
one of it's postings and splits those into two transactions.

Example:

    plugin "plugins.settle_inv" "Assets:PayPal"

    2017-04-03 * "" ""
        Assets:Checkings        -100.00 EUR
            paypal: 2017-04-01
        Expenses:Something

    ; becomes

    2017-04-01 * "" "Doing some saving transfers" ^settle-43be1c
        Assets:PayPal           -100.00 EUR
        Expenses:Something

    2017-04-03 * "" "Settle: Doing some saving transfers" ^settle-43be1c
        Assets:Checkings        -100.00 EUR
        Assets:PayPal            100.00 EUR
"""

from dateutil.parser import parse

from beancount.core import data, compare

__plugins__ = ['settlement_date']


def settlement_date(entries, options_map, config):
    # config = PayPal account
    new_entries = []
    errors = []

    for index, entry in enumerate(entries):
        if isinstance(entry, data.Transaction):
            added = False
            for p_index, posting in enumerate(entry.postings):
                if posting.meta and 'paypal' in posting.meta:

                    s_date = entry.date
                    link = 'paypal-{}'.format(compare.hash_entry(entry)[:12])
                    original_account = posting.account

                    m_links = set(entry.links).union([link]) \
                            if entry.links else set([link])

                    m_postings = entry.postings
                    m_postings[p_index] = m_postings[p_index]._replace(meta=dict())
                    m_postings[p_index] = m_postings[p_index]._replace(account=config)
                    m_date = posting.meta['paypal']

                    new_posting = entry.postings[p_index]
                    new_posting = new_posting._replace(meta=dict())

                    # remove unintended additioal meta-fields
                    # (which could trigger additional plugins)
                    s_meta = dict()
                    s_meta['filename'] = entry.meta['filename']
                    s_meta['lineno'] = entry.meta['lineno']
                    s_meta['__tolerances__'] = entry.meta['__tolerances__']

                    s_postings = [
                        new_posting,
                        new_posting
                    ]

                    s_postings[0] = s_postings[0]._replace(account=original_account)
                    s_postings[1] = s_postings[1]._replace(account=config)
                    s_postings[1] = s_postings[1]._replace(units=entry.postings[p_index].units._replace(number=entry.postings[p_index].units.number*-1))

                    modified_transaction = data.Transaction(entry.meta, m_date,
                        entry.flag, '', entry.narration,
                        entry.tags, m_links, m_postings)

                    settling_transaction = data.Transaction(s_meta, s_date,
                        entry.flag, '', 'Settle: {}'.format(entry.narration),
                        entry.tags, set([link]), s_postings)

                    new_entries.append(modified_transaction)
                    new_entries.append(settling_transaction)

                    added = True
                    break

            if not added:
                new_entries.append(entry)
        else:
            new_entries.append(entry)
    return new_entries, errors
