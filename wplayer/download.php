<?php
// Sends this folder's video as a download rather than letting the browser play it.
// wprep.py copies this next to index.html; the Download item in the player's settings menu points here.
// Takes no parameters: it only ever serves the one .mp4 in its own folder.

$videos = array_values(array_filter(scandir(__DIR__), function ($f) {
    return strtolower(substr($f, -4)) === '.mp4' && is_file(__DIR__ . '/' . $f);
}));
if (count($videos) !== 1) {
    http_response_code(404);
    exit("No video here.\n");
}
$name = $videos[0];
$file = __DIR__ . '/' . $name;

set_time_limit(0);
while (ob_get_level()) {
    ob_end_clean();
}
// filename= is a plain-ASCII fallback for old browsers; filename*= carries the real (UTF-8) name.
$ascii = preg_replace('/[^\x20-\x7e]|["\\\\]/', '_', $name);
header('Content-Type: video/mp4');
header('Content-Length: ' . filesize($file));
header("Content-Disposition: attachment; filename=\"$ascii\"; filename*=UTF-8''" . rawurlencode($name));
readfile($file);
