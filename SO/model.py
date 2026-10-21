"""Modelo independente do estado observável do exercício 1 de CloudIST."""

from run_tests import END, STATUS, normalise


class Model:
    def __init__(self, servers=4, ram=256, disk=512, cpu=128):
        self.args = (servers, ram, disk, cpu)
        self.types = {}
        self.reservations = {}

    def define(self, name, ram=1, disk=1, cpu=1, folder="@INPUT@", exe="@EXE@"):
        if name in self.types:
            raise ValueError(f"Tipo repetido: {name}")
        self.types[name] = (ram, disk, cpu, folder, exe)

    def vms(self):
        result = []
        for rid, requests in self.reservations.items():
            number = 0
            for name, amount, server in requests:
                for _ in range(amount):
                    number += 1
                    result.append((rid, f"{rid}_{number}", name, server))
        return result

    def used(self, server):
        vms = [vm for vm in self.vms() if vm[3] == server]
        return tuple(sum(self.types[vm[2]][i] for vm in vms) for i in range(3))

    def reserve(self, rid, requests):
        if rid in self.reservations or not requests:
            raise ValueError("Reserva repetida ou vazia")
        servers, ram, disk, cpu = self.args
        used = {s: list(self.used(s)) for s in range(1, servers + 1)}
        for name, amount, server in requests:
            if name not in self.types or amount < 1 or server not in used:
                raise ValueError("Pedido de reserva inválido")
            for i, total in enumerate((ram, disk, cpu)):
                used[server][i] += self.types[name][i] * amount
                if used[server][i] > total:
                    raise ValueError("Recursos insuficientes")
        self.reservations[rid] = list(requests)

    def listing(self):
        servers, ram, disk, cpu = self.args
        line = "-" * 90
        out = [STATUS, f"[ PHYSICAL SERVERS ] ({servers} total)", line]
        all_vms = self.vms()
        for server in range(1, servers + 1):
            used_ram, used_disk, used_cpu = self.used(server)
            hosted = [vm for vm in all_vms if vm[3] == server]
            out += [f"Server #{server}",
                    f"├─ Resources Total : {cpu:.2f} vCPUs | {ram} GB RAM | {disk} GB Disk",
                    f"├─ Resources Used : {used_cpu:.2f} vCPUs | {used_ram} GB RAM | {used_disk} GB Disk",
                    f"├─ Resources Available : {cpu-used_cpu:.2f} vCPUs | {ram-used_ram} GB RAM | {disk-used_disk} GB Disk",
                    f"└─ Hosted VMs ({len(hosted)}):"]
            if not hosted:
                out.append("(None)")
            for i, (_, vid, name, _) in enumerate(hosted):
                branch = "└──" if i == len(hosted) - 1 else "├──"
                out.append(f"{branch} VM ID : {vid} | Type: {name} | State: RESERVED")
        out += [f"[ DEFINED VM TYPES ] ({len(self.types)} registered)", line]
        if not self.types:
            out.append("(None)")
        for name, (r, d, c, folder, exe) in self.types.items():
            out += [f"* Type ID: {name} | Requirements: {c:.2f} vCPU, {r} GB RAM, {d} GB Disk",
                    f"├─ Executable : {exe}", f"└─ Input Dir : {folder}"]
        out += [f"[ RESERVATIONS ] ({len(self.reservations)} total)", line]
        if not self.reservations:
            out.append("(None)")
        for rid, requests in self.reservations.items():
            vms = [vm for vm in all_vms if vm[0] == rid]
            out += [f"* Reservation ID: {rid} | State: PENDING | Total VMs: {len(vms)}", "├─ Requested Pairs:"]
            out += [f"│ • {name} : {amount} unit(s)" for name, amount, _ in requests]
            out.append("└─ Allocated VMs:")
            for i, (_, vid, _, server) in enumerate(vms):
                branch = "└──" if i == len(vms) - 1 else "├──"
                out.append(f"{branch} ID: {vid} | Host Server: #{server}")
        return normalise("\n".join([*out, END]))
