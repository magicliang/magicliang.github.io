import argparse
import json
import os
import pathlib
import tempfile


def snapshot(cgroup):
    if cgroup is None:
        return None
    return (cgroup / 'io.stat').read_text()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workdir', required=True, type=pathlib.Path)
    parser.add_argument('--cgroup', type=pathlib.Path)
    parser.add_argument('--bytes', type=int, default=262144)
    args = parser.parse_args()
    if not 1 <= args.bytes <= 1048576:
        parser.error('--bytes must be between 1 and 1048576')
    workdir = args.workdir.resolve(strict=True)
    if not workdir.is_dir():
        parser.error('--workdir must be an existing directory')
    cgroup = args.cgroup.resolve(strict=True) if args.cgroup else None
    before = snapshot(cgroup)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', prefix='io-probe-', dir=workdir, delete=False) as output:
            temporary = pathlib.Path(output.name)
            remaining = args.bytes
            while remaining:
                chunk = min(remaining, 4096)
                output.write(b'x' * chunk)
                remaining -= chunk
            output.flush()
            os.fsync(output.fileno())
        after = snapshot(cgroup)
        device = os.stat(workdir).st_dev
        result = {
            'bytes_written': args.bytes,
            'workdir_device': f'{os.major(device)}:{os.minor(device)}',
            'cgroup': str(cgroup) if cgroup else None,
            'self_cgroup': pathlib.Path('/proc/self/cgroup').read_text(),
            'io_stat_before': before,
            'io_stat_after': after,
            'read_only_observation': cgroup is not None,
        }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    result['cleanup_file_absent'] = temporary is not None and not temporary.exists()
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
