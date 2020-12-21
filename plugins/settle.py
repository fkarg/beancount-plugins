"""Beancount plugin to split transactions which are in transit.

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


    ; also; in case of settling negative parts later:
    2017-04-01 * "" ""
        Assets:Savings:US               -100.00 USD
            settle: 2017-04-03
        Assets:Savings:JP

    ; becomes

    2017-04-01 * "" "Doing some saving transfers" ^settle-43be1c
        Liabilities:AccountsPayable     -100.00 USD
            settle: 2017-04-03
        Assets:Savings:JP                100.00 USD

    2017-04-03 * "" "Settle: Doing some saving transfers" ^settle-43be1c
        Assets:Savings:US               -100.00 USD
        Liabilities:AccoutsPayable       100.00 USD
"""

from datetime import date
from dateutil.parser import parse

from beancount.core import data, compare

__plugins__ = ["settlement_date"]


def settlement_date(entries, options_map, config):
    errors = []

    for index, entry in enumerate(entries):
        if isinstance(entry, data.Transaction):
            for p_index, posting in enumerate(entry.postings):
                if posting.meta and "settle" in posting.meta:
                    save_config = None
                    postings = entry.postings
                    s_date = posting.meta["settle"]
                    link = "settle-{}".format(compare.hash_entry(entry))
                    original_account = posting.account
                    if postings[p_index].units.number < 0:
                        save_config = config
                        config = "Liabilities:AccountsPayable"
                    entry.postings[p_index] = entry.postings[p_index]._replace(
                        account=config
                    )
                    links = (
                        set(entries[index].links).union([link]) if entries[index].links else set([link])
                    )
                    entries[index] = entry._replace(postings=postings)
                    entries[index] = entry._replace(links=links)

                    # do not settle future dates yet
                    if s_date >= date.today():
                        config = save_config if save_config else config
                        continue

                    new_posting = postings[p_index]
                    new_posting = new_posting._replace(meta=dict())

                    postings = [new_posting, new_posting]

                    postings[0] = postings[0]._replace(account=config)
                    postings[0] = postings[0]._replace(
                        units=postings[1].units._replace(
                            number=postings[1].units.number * -1
                        )
                    )
                    postings[1] = postings[1]._replace(account=original_account)

                    if save_config:
                        postings.reverse()

                    entries.append(
                        data.Transaction(
                            entry.meta,
                            s_date,
                            entry.flag,
                            "",
                            "Settle: {}".format(entry.narration),
                            entry.tags,
                            set([link]),
                            postings,
                        )
                    )

                    config = save_config if save_config else config
                    # break # allow use of multiple 'settle'
    return entries, errors
