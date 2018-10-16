from mock import patch

from pip._internal.vcs.subversion import Subversion


@patch('pip._internal.vcs.call_subprocess')
def test_obtain_should_recognize_auth_info_url(call_subprocess_mock, script):
    svn = Subversion(url='svn+http://username:password@svn.example.com/')
    svn.obtain(script.scratch_path / 'test')
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'checkout', '-q', '--username', 'username', '--password',
        'password', 'http://svn.example.com/',
        script.scratch_path / 'test',
    ]


@patch('pip._internal.vcs.call_subprocess')
def test_export_should_recognize_auth_info_url(call_subprocess_mock, script):
    svn = Subversion(url='svn+http://username:password@svn.example.com/')
    svn.export(script.scratch_path / 'test')
    assert call_subprocess_mock.call_args[0][0] == [
        svn.name, 'export', '--username', 'username', '--password',
        'password', 'http://svn.example.com/',
        script.scratch_path / 'test',
    ]
