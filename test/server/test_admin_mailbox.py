
from typing import Any, Optional

import pytest  # type: ignore
from pymapadmin.grpc.admin_pb2 import Login, AppendRequest, AppendResponse, \
    SUCCESS, FAILURE

from pymap.admin.handlers.mailbox import MailboxHandlers

from .base import TestBase

pytestmark = pytest.mark.asyncio


class _Stream:

    def __init__(self, request) -> None:
        self.request = request
        self.response: Optional[Any] = None

    async def recv_message(self) -> object:
        return self.request

    async def send_message(self, response) -> None:
        self.response = response


class TestMailboxHandlers(TestBase):

    async def test_append(self, backend, imap_server):
        handlers = MailboxHandlers(backend, True)
        data = b'From: user@example.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert SUCCESS == response.result.code
        assert 105 == response.uid

        transport = self.new_transport(imap_server)
        transport.push_login()
        transport.push_select(b'INBOX')
        transport.push_readline(
            b'fetch1 UID FETCH * FULL\r\n')
        transport.push_write(
            b'* 5 FETCH (FLAGS (\\Flagged \\Recent \\Seen)'
            b' INTERNALDATE "13-Feb-2009 23:31:30 +0000"'
            b' RFC822.SIZE 38'
            b' ENVELOPE (NIL NIL (("" NIL "user" "example.com"))'
            b' (("" NIL "user" "example.com")) (("" NIL "user" "example.com"))'
            b' NIL NIL NIL NIL NIL)'
            b' BODY ("text" "plain" NIL NIL NIL "7BIT" 38 3)'
            b' UID 105)\r\n'
            b'fetch1 OK UID FETCH completed.\r\n')
        transport.push_logout()
        await self.run(transport)

    async def test_append_user_not_found(self, backend):
        handlers = MailboxHandlers(backend, True)
        login = Login(authcid='testuser', secret='badpass')
        request = AppendRequest(login=login)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert FAILURE == response.result.code
        assert 'InvalidAuth' == response.result.key

    async def test_append_mailbox_not_found(self, backend):
        handlers = MailboxHandlers(backend, True)
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='BAD')
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert FAILURE == response.result.code
        assert 'BAD' == response.mailbox
        assert 'MailboxNotFound' == response.result.key

    async def test_append_filter_reject(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'Subject: reject this\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert FAILURE == response.result.code
        assert 'AppendFailure' == response.result.key

    async def test_append_filter_discard(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'Subject: discard this\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert SUCCESS == response.result.code
        assert not response.mailbox
        assert not response.uid

    async def test_append_filter_address_is(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'From: foo@example.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 1' == response.mailbox

    async def test_append_filter_address_contains(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'From: user@foo.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 2' == response.mailbox

    async def test_append_filter_address_matches(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'To: bigfoot@example.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 3' == response.mailbox

    async def test_append_filter_envelope_is(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'From: user@example.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                sender='foo@example.com', recipient=None,
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 4' == response.mailbox

    async def test_append_filter_envelope_contains(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'From: user@example.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                sender='user@foo.com', recipient=None,
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 5' == response.mailbox

    async def test_append_filter_envelope_matches(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'From: user@example.com\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                sender=None, recipient='bigfoot@example.com',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 6' == response.mailbox

    async def test_append_filter_exists(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'X-Foo: foo\nX-Bar: bar\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 7' == response.mailbox

    async def test_append_filter_header(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'X-Caffeine: C8H10N4O2\n\ntest message!\n'
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 8' == response.mailbox

    async def test_append_filter_size(self, backend):
        handlers = MailboxHandlers(backend, True)
        data = b'From: user@example.com\n\ntest message!\n'
        data = data + b'x' * (1234 - len(data))
        login = Login(authcid='testuser', secret='testpass')
        request = AppendRequest(login=login, mailbox='INBOX',
                                flags=['\\Flagged', '\\Seen'],
                                when=1234567890, data=data)
        stream = _Stream(request)
        await handlers.Append(stream)
        response: AppendResponse = stream.response
        assert 'Test 9' == response.mailbox