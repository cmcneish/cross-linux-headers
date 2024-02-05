import functools
from pathlib import Path
import shutil
import subprocess
import typing as T

versions_to_track = [
    # https://kernel.org/
    b'4.14.x',
    b'4.19.x',
    b'5.4.x',
    b'5.10.x',
    b'5.15.x',
    b'6.1.x',
    b'6.6.x',
]

linux_dir = Path('.').resolve()
cross_linux_headers_dir = Path(__file__).parent.resolve()

@functools.cache
def git_tag_list(repo: Path):
    tags_str = subprocess.check_output(
        ['git', 'tag', '-l'],
        cwd=repo)

    return tags_str.strip().split(b'\n')

class TagOps:
    @staticmethod
    def get_version_tags(version: bytes):
        tags = git_tag_list(linux_dir)

        version_prefix = b'v' + version.replace(b'.x', b'.')

        matching_tags = []
        for tag in tags:
            if tag.startswith(version_prefix) and b'rc' not in tag:
                matching_tags.append(tag)

        return matching_tags

    @staticmethod
    def tag_key(tag: bytes):
        assert(tag.startswith(b'v'))
        return tuple(int(x) for x in tag[1:].split(b'.'))

    @staticmethod
    def get_version_start(version: bytes):
        version_file = cross_linux_headers_dir / version.decode('utf-8') / '.version'
        if version_file.exists():
            return version_file.read_bytes().strip()

        return None

    @staticmethod
    def get_version_stop(tags: T.List[bytes]):
        return max(tags, key=TagOps.tag_key)

def get_update_range(tags, start, stop):
    version_range = []

    sorted_tags = sorted(tags, key=TagOps.tag_key)

    if start is None:
        start = min(tags, key=TagOps.tag_key)
        start_idx = sorted_tags.index(start)
    else:
        if start not in tags:
            raise RuntimeError('unknown start tag')

        start_idx = sorted_tags.index(start) + 1
        start = sorted_tags[start_idx]

    if stop not in tags:
        raise RuntimeError('unknown stop tag')

    stop_idx = sorted_tags.index(stop)

    version_range = sorted_tags[start_idx:stop_idx+1]

    assert(version_range[0] == start), (version_range, start)
    assert(version_range[-1] == stop)

    return version_range

def clean_dir(d: Path):
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(exist_ok=True, parents=True)

    assert(not list(d.iterdir())), 'clean_dir failed'

def do_update(version, update):
    version_str = version.decode('utf-8')
    update_str = update.decode('utf-8')

    version_dir = cross_linux_headers_dir / version_str
    version_file = version_dir / '.version'

    clean_dir(version_dir)

    # print(update)

    tag = update_str

    subprocess.check_call(
        ['git', 'checkout', '-f', tag],
        cwd=linux_dir)

    arches = set(x.name for x in (linux_dir / 'arch').iterdir())

    arch_filter = set((
        # Not architectures
        'Kconfig',
        '.gitignore',

        # Makefile:1161: *** Headers not exportable for the um architecture.  Stop.
        'um',
    ))

    arches = arches - arch_filter

    for arch in sorted(arches):
        # riscv in v4.14.312
        if not (linux_dir / 'arch' / arch / 'Makefile').exists():
            print('skipping', tag, arch, 'due to no Makefile')
            continue

        print('processing', tag, arch)

        version_arch_dir = version_dir / arch
        version_arch_dir.mkdir(exist_ok=True, parents=True)

        subprocess.check_call(
            ['git', 'clean', '-dxf'],
            cwd=linux_dir,
            stdout=subprocess.DEVNULL)

        with open(version_arch_dir / 'stdout.txt', 'wb') as out_f:
            with open(version_arch_dir / 'stderr.txt', 'wb') as err_f:

                subprocess.check_call(
                    [
                        'make',
                        f'ARCH={arch}',
                        f'INSTALL_HDR_PATH={version_arch_dir.as_posix()}',
                        'headers_install',
                    ],
                    stdout=out_f,
                    stderr=err_f,
                    cwd=linux_dir)

    version_file.write_bytes(update)

    print('arch updates done')

    print('staging commit')

    subprocess.check_call(
        ['git', 'add', '-fA', version_dir],
        cwd=cross_linux_headers_dir)

    print('making commit')

    subprocess.check_call(
        ['git', 'commit', '-m', f'Update {version_str} to {update_str}'],
        cwd=cross_linux_headers_dir)

def main():
    # * for each version to track:
    #   * find folder corresponding to tracked headers
    #   * determine progress based on upstream, downstream
    #   * for each missing commit:
    #     * build each arch's headers
    #     * make a commit in folder

    # Normalize local branches
    for version in versions_to_track:
        tags = TagOps.get_version_tags(version)
        version_start = TagOps.get_version_start(version)
        version_stop = TagOps.get_version_stop(tags)

        if version_start == version_stop:
            continue

        version_range = get_update_range(tags, version_start, version_stop)

        print('updating', version_range[0].decode('utf-8'), '->', version_range[-1].decode('utf-8'))

        for update in version_range:
            do_update(version, update)

if __name__ == '__main__':
    main()
