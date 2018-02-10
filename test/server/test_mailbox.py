
import pytest

from .base import TestBase

pytestmark = pytest.mark.asyncio


class TestMailbox(TestBase):

    async def test_list(self):
        self.login()
        self.transport.push_readline(
            b'list1 LIST "" ""\r\n')
        self.transport.push_write(
            b'* LIST () "." INBOX\r\n'
            b'* LIST () "." Sent\r\n'
            b'* LIST () "." Trash\r\n'
            b'list1 OK LIST completed.\r\n')
        self.logout()
        await self.run()

    async def test_status(self):
        self.login()
        self.transport.push_readline(
            b'status1 STATUS INBOX '
            b'(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)\r\n')
        self.transport.push_write(
            b'* STATUS INBOX (MESSAGES 4 RECENT 1 UIDNEXT 104 '
            b'UIDVALIDITY ', (br'\d+', b'uidval1'), b' UNSEEN 1)\r\n'
            b'status1 OK STATUS completed.\r\n')
        self.select(b'INBOX', 4, 1, 104, 4)
        self.transport.push_readline(
            b'status2 STATUS INBOX '
            b'(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)\r\n')
        self.transport.push_write(
            b'* STATUS INBOX (MESSAGES 4 RECENT 0 UIDNEXT 104 '
            b'UIDVALIDITY ', (br'\d+', b'uidval2'), b' UNSEEN 1)\r\n'
            b'status2 OK STATUS completed.\r\n')
        self.logout()
        await self.run()
        assert self.matches['uidval1'] == self.matches['uidval2']

    async def test_append(self):
        message = b'test message\r\n'
        self.login()
        self.transport.push_readline(
            b'append1 APPEND INBOX (\\Seen) {%i}\r\n' % len(message))
        self.transport.push_write(
            b'+ Literal string\r\n')
        self.transport.push_readexactly(message)
        self.transport.push_readline(
            b'\r\n')
        self.transport.push_write(
            b'append1 OK APPEND completed.\r\n')
        self.select(b'INBOX', 5, 2, 105, 4)
        self.logout()
        await self.run()

    async def test_append_selected(self):
        message = b'test message\r\n'
        self.login()
        self.select(b'INBOX', 4, 1, 104, 4)
        self.transport.push_readline(
            b'append1 APPEND INBOX (\\Seen) {%i}\r\n' % len(message))
        self.transport.push_write(
            b'+ Literal string\r\n')
        self.transport.push_readexactly(message)
        self.transport.push_readline(
            b'\r\n')
        self.transport.push_write(
            b'* 5 EXISTS\r\n'
            b'* 2 RECENT\r\n'
            b'* 5 FETCH (FLAGS (\\Recent \\Seen))\r\n'
            b'append1 OK APPEND completed.\r\n')
        self.logout()
        await self.run()
