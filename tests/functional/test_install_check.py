from tests.lib import create_basic_wheel_for_package


def matches_expected_lines(string, expected_lines):
    return set(string.splitlines()) == set(expected_lines)


def test_check_install_canonicalization(script):
    pkga_path = create_basic_wheel_for_package(
        script.scratch_path, 'pkgA', '1.0',
        depends=['normal-missing', 'SPECIAL.missing'],
    )
    normal_path = create_basic_wheel_for_package(
        script.scratch_path, 'normal-missing', '0.1',
    )
    special_path = create_basic_wheel_for_package(
        script.scratch_path, 'SPECIAL.missing', '0.1',
    )

    # Let's install pkgA without its dependency
    result = script.pip_install_local(pkga_path, '--no-deps', links=None)
    assert "Successfully installed pkgA-1.0" in result.stdout, str(result)

    # Install the first missing dependency. Only an error for the
    # second dependency should remain.
    result = script.pip_install_local(
        normal_path, '--quiet', expect_error=True, links=None,
    )
    expected_lines = [
        "pkga 1.0 requires SPECIAL.missing, which is not installed.",
    ]
    assert matches_expected_lines(result.stderr, expected_lines)
    assert result.returncode == 0

    # Install the second missing package and expect that there is no warning
    # during the installation. This is special as the package name requires
    # name normalization (as in https://github.com/pypa/pip/issues/5134)
    result = script.pip_install_local(
        special_path, '--quiet', links=None,
    )
    assert matches_expected_lines(result.stderr, [])
    assert result.returncode == 0

    # Double check that all errors are resolved in the end
    result = script.pip('check')
    expected_lines = [
        "No broken requirements found.",
    ]
    assert matches_expected_lines(result.stdout, expected_lines)
    assert result.returncode == 0


def test_check_install_does_not_warn_for_out_of_graph_issues(script):
    pkg_broken_path = create_basic_wheel_for_package(
        script.scratch_path, 'broken', '1.0',
        depends=['missing', 'conflict < 1.0'],
    )
    pkg_unrelated_path = create_basic_wheel_for_package(
        script.scratch_path, 'unrelated', '1.0',
    )
    pkg_conflict_path = create_basic_wheel_for_package(
        script.scratch_path, 'conflict', '1.0',
    )

    # Install a package without it's dependencies
    result = script.pip_install_local(pkg_broken_path, '--no-deps', links=None)
    assert matches_expected_lines(result.stderr, [])

    # Install conflict package
    result = script.pip_install_local(
        pkg_conflict_path, expect_error=True, links=None,
    )
    assert matches_expected_lines(result.stderr, [
        "broken 1.0 requires missing, which is not installed.",
        (
            "broken 1.0 has requirement conflict<1.0, but "
            "you'll have conflict 1.0 which is incompatible."
        ),
    ])

    # Install unrelated package
    result = script.pip_install_local(
        pkg_unrelated_path, '--quiet', links=None,
    )
    # should not warn about broken's deps when installing unrelated package
    assert matches_expected_lines(result.stderr, [])

    result = script.pip('check', expect_error=True)
    expected_lines = [
        "broken 1.0 requires missing, which is not installed.",
        "broken 1.0 has requirement conflict<1.0, but you have conflict 1.0.",
    ]
    assert matches_expected_lines(result.stdout, expected_lines)
