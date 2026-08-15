"""Launch GLSim with the genlayer-test 0.29.2 Windows fd-0 workaround."""

import os
import tempfile


def _patch_windows_loader() -> None:
    if os.name != "nt":
        return

    from gltest.direct import loader

    def inject_message_without_early_unlink(vm):
        try:
            from genlayer.py import calldata
            from genlayer.py.types import Address
        except ImportError:
            return

        sender = vm.sender
        if isinstance(sender, bytes):
            sender = Address(sender)
        contract = vm._contract_address
        if isinstance(contract, bytes):
            contract = Address(contract)
        origin = vm.origin
        if isinstance(origin, bytes):
            origin = Address(origin)

        encoded = calldata.encode(
            {
                "contract_address": contract,
                "sender_address": sender,
                "origin_address": origin,
                "stack": [],
                "value": vm._value,
                "datetime": vm._datetime,
                "is_init": False,
                "chain_id": vm._chain_id,
                "entry_kind": 0,
                "entry_data": b"",
                "entry_stage_data": None,
            }
        )
        fd, path = tempfile.mkstemp(prefix="schemacrosswalk-glsim-stdin-")
        os.write(fd, encoded)
        os.lseek(fd, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(fd, 0)
        os.close(fd)
        # fd 0 must remain attached until the contract module reads it. Windows
        # therefore cannot unlink this file here; the process is ephemeral.
        vm._schemacrosswalk_stdin_path = path

    loader._inject_message_to_fd0 = inject_message_without_early_unlink


_patch_windows_loader()

from glsim.__main__ import main


if __name__ == "__main__":
    main()
