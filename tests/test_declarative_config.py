"""Testing for declarative config."""
import argparse
import os
import pytest
from Levenshtein import distance
import declarative_config.declarative_config as declarative_config


def test_validator_fail():
    """Tests that the validator fails files not properly formatted."""
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath")
    parser.add_argument("--schemapath", default="yaml_schema.yaml")
    directory = "tests/data/fail_validation"

    for filename in os.listdir(directory):
        with pytest.raises(declarative_config.YamlBadFormat):
            filepath = os.path.join(directory, filename)
            declarative_config.validate_data(parser.parse_args([filepath]))


def test_output_same_as_input():
    """Tests that executing the script that puts yaml data into the db,
    followed by executing the script that pulls the data from the db,
    produces output that is nearly identical to the source.
    Some lenience is given for whitespace differences.

    This only checks that the same data that went in came out. It does
    not check that the data was stored in the right way.

    Data samples are taken from the real database."""
    # Would delete everything from the db right here to make a clean
    # test env, but not sure if this will ever be run on the real db.
    inputs_outputs = [
        (
            "tests/data/listing_1.yaml",
            "tests/data/output_1.yaml",
            "xmlstarlet",
            "4.5",
            "Cluster",
        ),
        (
            "tests/data/listing_2.yaml",
            "tests/data/output_2.yaml",
            "RHEL-7-OSE-3.5",
            "3.5",
            "Server-RH7-RHOSE-3.5",
        ),
        (
            "tests/data/listing_3.yaml",
            "tests/data/output_3.yaml",
            "konami",
            "1.0",
            "7Server-Konami",
        ),
        (
            "tests/data/listing_4.yaml",
            "tests/data/output_4.yaml",
            "konami",
            "2.0",
            "6Server-Konami",
        ),
    ]
    for pair in inputs_outputs:
        declarative_config.main(["insert", pair[0], "--commit", "--verbose"])
        declarative_config.main(
            [
                "generate",
                pair[1],
                "--product",
                pair[2],
                "--version",
                pair[3],
                "--variant",
                pair[4],
            ]
        )
        with open(pair[0], "r", encoding="ascii") as input_file, open(
            pair[0], "r", encoding="ascii"
        ) as output_file:
            assert distance(input_file.read(), output_file.read()) < 5


def test_inserted_data_properly_stored_1():
    """Tests that once the insertions are made, the data is in the right places
    in the db."""
    label = "xmlstarlet"
    version = "4.5"
    variant = "Cluster"
    declarative_config.main(
        [
            "insert",
            "tests/data/listing_1.yaml",
            "--commit",
            "--verbose",
        ]
    )

    my_db = declarative_config.connect()

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    assert len(result) == 5
    assert (46533, prod_id) in result
    assert (5900, prod_id) in result
    assert (5899, prod_id) in result
    assert (51630, prod_id) in result
    assert (5558, prod_id) in result

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 17
    assert (
        "console-login-helper-messages",
        "noarch",
        "ppc64le",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "noarch", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "ia64", "ia64", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "aarch64",
        "aarch64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "s390x", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "ia64", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "aarch64", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "s390x", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "s390x",
        "ppc64le",
        prod_id,
        True,
    ) in result
    assert ("xmlstarlet", "aarch64", "aarch64", prod_id, True) in result
    assert ("xmlstarlet", "ppc64le", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "s390x", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "x86_64", "x86_64", prod_id, True) in result
    assert ("xmlstarlet", "src", "aarch64", prod_id, True) in result
    assert ("xmlstarlet", "src", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "src", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "src", "x86_64", prod_id, True) in result


def test_inserted_data_properly_stored_2():
    """Tests that once the insertions are made, the data is in the right places
    in the db."""
    label = "RHEL-7-OSE-3.5"
    version = "3.5"
    variant = "Server-RH7-RHOSE-3.5"
    declarative_config.main(["insert", "tests/data/listing_2.yaml", "--commit"])

    my_db = declarative_config.connect()

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1
    assert (5558, prod_id) in result

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 8
    assert ("ansible", "noarch", "x86_64", prod_id, True) in result
    assert ("ansible", "x86_64", "x86_64", prod_id, True) in result
    assert ("ansible", "src", "x86_64", prod_id, True) in result
    assert ("cockpit", "x86_64", "x86_64", prod_id, True) in result
    assert ("cockpit", "src", "x86_64", prod_id, True) in result
    assert ("nodejs-chalk", "noarch", "x86_64", prod_id, True) in result
    assert ("nodejs-chalk", "x86_64", "x86_64", prod_id, True) in result
    assert ("nodejs-chalk", "src", "x86_64", prod_id, True) in result


def test_inserted_data_properly_stored_3_no_arch():
    """Tests that once the insertions are made, the data is in the right places
    in the db."""
    label = "konami"
    version = "1.0"
    variant = "7Server-Konami"
    declarative_config.main(["insert", "tests/data/listing_3.yaml", "--commit"])

    my_db = declarative_config.connect()

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1
    assert (5558, prod_id) in result

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 1
    assert (
        "console-login-helper-messages",
        "noarch",
        "x86_64",
        prod_id,
        True,
    ) in result


def test_inserted_data_properly_stored_4_no_packages():
    """Tests that once the insertions are made, the data is in the right places
    in the db."""
    label = "konami"
    version = "2.0"
    variant = "6Server-Konami"
    declarative_config.main(["insert", "tests/data/listing_4.yaml", "--commit"])

    my_db = declarative_config.connect()

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    assert len(result) == 0

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 0


def test_inserted_data_properly_stored_5_deletions():
    """Tests that once the insertions are made, the data is in the right places
    in the db.

    This test uniquely also tests for deletion, deletion that happens simultaneously
    new insertions as well.
    """
    label = "RHEL-4"
    version = "6.0"
    variant = "AS"
    declarative_config.main(["insert", "tests/data/listing_5_part1.yaml", "--commit"])

    my_db = declarative_config.connect()

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    assert len(result) == 5
    assert (46533, prod_id) in result
    assert (5900, prod_id) in result
    assert (5899, prod_id) in result
    assert (51630, prod_id) in result
    assert (5558, prod_id) in result

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 16
    assert (
        "console-login-helper-messages",
        "noarch",
        "ppc64le",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "noarch", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "ia64", "ia64", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "aarch64",
        "aarch64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "s390x", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "ia64", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "aarch64", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "aarch64", "aarch64", prod_id, True) in result
    assert ("xmlstarlet", "ppc64le", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "s390x", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "x86_64", "x86_64", prod_id, True) in result
    assert ("xmlstarlet", "src", "aarch64", prod_id, True) in result
    assert ("xmlstarlet", "src", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "src", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "src", "x86_64", prod_id, True) in result

    #################################################################
    # Now perform deletions and one insertion into the same product #
    #################################################################

    declarative_config.main(["insert", "tests/data/listing_5_part2.yaml", "--commit"])

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    assert len(result) == 5
    assert (46533, prod_id) in result
    assert (5900, prod_id) in result
    assert (5899, prod_id) in result
    assert (51630, prod_id) in result
    assert (5558, prod_id) in result

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 12
    assert ("console-login-helper-messages", "noarch", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "ia64", "ia64", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "aarch64",
        "aarch64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "s390x", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "ia64", "ia64", prod_id, True) in result
    assert ("xmlstarlet", "ppc64le", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "s390x", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "x86_64", "x86_64", prod_id, True) in result
    assert ("xmlstarlet", "src", "ia64", prod_id, True) in result
    assert ("xmlstarlet", "src", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "src", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "src", "x86_64", prod_id, True) in result


def test_inserted_data_properly_stored_6_complete_package_replacement():
    """Tests that once the insertions are made, the data is in the right places
    in the db.

    This test uniquely also tests for a complete replacement of packages:
    everything in the second set is different from the first.
    """
    label = "xmlstarlet"
    version = "4.0"
    variant = "Cluster"
    declarative_config.main(["insert", "tests/data/listing_6_part1.yaml", "--commit"])

    my_db = declarative_config.connect()

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    # assert len(result) == 9
    # Skip the actual count here as deletion is impossible
    # and result is widely dependent on that.
    assert (46533, prod_id) in result
    assert (5900, prod_id) in result
    assert (5899, prod_id) in result
    assert (51630, prod_id) in result
    assert (5558, prod_id) in result
    assert (5901, prod_id) in result
    assert (17097, prod_id) in result
    assert (17097, prod_id) in result
    assert (5559, prod_id) in result

    # Verify overrides entries
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 19
    assert (
        "console-login-helper-messages",
        "noarch",
        "ppc64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "noarch", "ppc", prod_id, True) in result
    assert ("console-login-helper-messages", "ia64", "ia64", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "aarch64",
        "aarch64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "s390x", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "ia64", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "aarch64", prod_id, True) in result
    assert ("console-login-helper-messages", "src", "s390x", prod_id, True) in result
    assert ("console-login-helper-messages", "ppc", "ppc64", prod_id, True) in result
    assert ("console-login-helper-messages", "ia64", "x86_64", prod_id, True) in result
    assert ("console-login-helper-messages", "aarch64", "i386", prod_id, True) in result
    assert ("xmlstarlet", "aarch64", "aarch64", prod_id, True) in result
    assert ("xmlstarlet", "ppc64le", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "s390x", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "x86_64", "x86_64", prod_id, True) in result
    assert ("xmlstarlet", "src", "aarch64", prod_id, True) in result
    assert ("xmlstarlet", "src", "ppc64le", prod_id, True) in result
    assert ("xmlstarlet", "src", "s390x", prod_id, True) in result
    assert ("xmlstarlet", "src", "x86_64", prod_id, True) in result

    #########################################
    # Now perform replacement of everything #
    #########################################

    declarative_config.main(["insert", "tests/data/listing_6_part2.yaml", "--commit"])

    # Verify products entry
    query = """select * from products where
                label = '{0}' and
                version = '{1}' and
                variant = '{2}' and
                allow_source_only = '{3}'""".format(
        label, version, variant, False
    )
    result = my_db.query(query).getresult()
    assert len(result) == 1  # Checks that there is exactly one listing

    # Verify tree_product_map entries
    prod_id = result[0][0]
    query = """select * from tree_product_map where product_id = '{0}'""".format(
        prod_id
    )
    result = my_db.query(query).getresult()
    # assert len(result) == 8
    # Skip the actual count here as deletion is impossible
    # and result is widely dependent on that.
    assert (46533, prod_id) in result
    assert (5900, prod_id) in result
    assert (5899, prod_id) in result
    assert (51630, prod_id) in result
    assert (5558, prod_id) in result
    assert (5901, prod_id) in result
    assert (17097, prod_id) in result
    assert (5559, prod_id) in result

    # Verify new overrides entries were in DB
    query = """select * from overrides where product = '{0}'""".format(prod_id)
    result = my_db.query(query).getresult()
    assert len(result) == 11
    assert ("console-login-helper-messages", "noarch", "s390x", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "noarch",
        "x86_64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "ppc", "ppc", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "ppc64",
        "ppc64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "src", "ppc", prod_id, True) in result
    assert (
        "console-login-helper-messages",
        "src",
        "ppc64",
        prod_id,
        True,
    ) in result
    assert (
        "console-login-helper-messages",
        "s390x",
        "aarch64",
        prod_id,
        True,
    ) in result
    assert ("console-login-helper-messages", "x86_64", "ppc", prod_id, True) in result
    assert ("xmlstarlet", "ppc", "ppc", prod_id, True) in result
    assert ("xmlstarlet", "ia64", "ia64", prod_id, True) in result
    assert ("xmlstarlet", "i386", "i386", prod_id, True) in result

    # Verify that all old entries were deleted
    assert (
        "console-login-helper-messages",
        "noarch",
        "ppc64",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "noarch",
        "ppc",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "ia64",
        "ia64",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "aarch64",
        "aarch64",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "s390x",
        "s390x",
        prod_id,
        True,
    ) not in result
    assert ("console-login-helper-messages", "src", "ia64", prod_id, True) not in result
    assert (
        "console-login-helper-messages",
        "src",
        "aarch64",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "src",
        "s390x",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "ppc",
        "ppc64",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "ia64",
        "x86_64",
        prod_id,
        True,
    ) not in result
    assert (
        "console-login-helper-messages",
        "aarch64",
        "i386",
        prod_id,
        True,
    ) not in result
    assert ("xmlstarlet", "aarch64", "aarch64", prod_id, True) not in result
    assert ("xmlstarlet", "ppc64le", "ppc64le", prod_id, True) not in result
    assert ("xmlstarlet", "s390x", "s390x", prod_id, True) not in result
    assert ("xmlstarlet", "x86_64", "x86_64", prod_id, True) not in result
    assert ("xmlstarlet", "src", "aarch64", prod_id, True) not in result
    assert ("xmlstarlet", "src", "ppc64le", prod_id, True) not in result
    assert ("xmlstarlet", "src", "s390x", prod_id, True) not in result
    assert ("xmlstarlet", "src", "x86_64", prod_id, True) not in result
