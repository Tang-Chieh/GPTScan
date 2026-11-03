"""Resolve a local image reference to one immutable ID; never pull or substitute."""
import re
import subprocess


def image_id(reference):
    if re.fullmatch(r"(?:sha256:)?[0-9a-f]{12,64}", reference):
        selected = reference
    else:
        listing = subprocess.check_output(["docker", "image", "ls", "--no-trunc", "--filter",
                                           "reference=" + reference, "--format", "{{.ID}}"], text=True)
        matches = set(listing.split())
        if len(matches) != 1:
            raise ValueError("Requested local Docker image must resolve to exactly one ID; no automatic pull")
        selected = matches.pop()
    resolved = subprocess.check_output(["docker", "image", "inspect", selected,
                                       "--format", "{{.Id}}"], text=True).strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", resolved):
        raise ValueError("Docker returned an invalid image digest")
    return resolved
