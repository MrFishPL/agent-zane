"""GraphQL query strings for the Nexar/Octopart API."""

# Full part fields fragment used across queries
PART_FIELDS = """
    mpn
    name
    shortDescription
    octopartUrl
    totalAvail
    manufacturer {
        name
        homepageUrl
    }
    category {
        id
        name
        path
    }
    medianPrice1000 {
        quantity
        price
        currency
        convertedPrice
        convertedCurrency
    }
    bestDatasheet {
        url
    }
    specs {
        attribute {
            name
            shortname
        }
        displayValue
    }
    sellers(authorizedOnly: true) {
        company {
            name
        }
        offers {
            sku
            inventoryLevel
            moq
            orderMultiple
            factoryLeadDays
            packaging
            prices {
                quantity
                price
                currency
                convertedPrice
                convertedCurrency
            }
            clickUrl
            updated
        }
    }
"""

SEARCH_PARTS = """
query SearchParts($q: String!, $start: Int, $limit: Int, $currency: String!, $country: String!) {
    supSearch(q: $q, start: $start, limit: $limit, currency: $currency, country: $country) {
        hits
        results {
            part {
                %s
            }
        }
    }
}
""" % PART_FIELDS

SEARCH_MPN = """
query SearchMPN($q: String!, $limit: Int, $currency: String!, $country: String!) {
    supSearchMpn(q: $q, limit: $limit, currency: $currency, country: $country) {
        hits
        results {
            part {
                %s
            }
        }
    }
}
""" % PART_FIELDS

MULTI_MATCH = """
query MultiMatch($queries: [SupPartMatchQuery!]!, $currency: String!, $country: String!) {
    supMultiMatch(queries: $queries, currency: $currency, country: $country) {
        hits
        parts {
            %s
        }
    }
}
""" % PART_FIELDS

CHECK_LIFECYCLE = """
query CheckLifecycle($q: String!) {
    supSearchMpn(q: $q, limit: 1) {
        hits
        results {
            part {
                mpn
                manufacturer {
                    name
                }
                shortDescription
                specs {
                    attribute {
                        shortname
                    }
                    displayValue
                }
            }
        }
    }
}
"""
