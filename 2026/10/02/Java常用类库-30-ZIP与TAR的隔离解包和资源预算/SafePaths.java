package blog.libraries.io;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;

public final class SafePaths {
    private SafePaths() { }

    public static Path resolveNewFile(Path privateRoot, String name) throws IOException {
        if (name == null || name.isEmpty() || name.indexOf('\0') >= 0
                || name.indexOf('\\') >= 0 || name.indexOf(':') >= 0 || name.startsWith("/")) {
            throw new IOException("invalid archive path");
        }
        Path root = privateRoot.toRealPath();
        Path relative = root.getFileSystem().getPath(name);
        if (relative.isAbsolute()) {
            throw new IOException("absolute path");
        }
        for (Path part : relative) {
            if (part.toString().equals("..") || part.toString().equals(".")) {
                throw new IOException("relative traversal");
            }
        }
        Path target = root.resolve(relative).normalize();
        if (!target.startsWith(root) || target.equals(root)) {
            throw new IOException("path outside root");
        }
        Path parent = target.getParent();
        Path current = root;
        for (Path part : root.relativize(parent)) {
            current = current.resolve(part);
            if (!Files.exists(current, LinkOption.NOFOLLOW_LINKS)) {
                Files.createDirectory(current);
            }
            if (Files.isSymbolicLink(current) || !Files.isDirectory(current, LinkOption.NOFOLLOW_LINKS)) {
                throw new IOException("unsafe parent");
            }
        }
        if (!parent.toRealPath().startsWith(root)
                || Files.exists(target, LinkOption.NOFOLLOW_LINKS)) {
            throw new IOException("existing or outside target");
        }
        return target;
    }
}
