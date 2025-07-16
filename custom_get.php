<?php

if(!isset($argv[1])) {
    exit("No URL given.\n");
}

$downloader = 'aria2c';
if(isset($argv[2])) {
    $downloader = $argv[2];
}

$url = $argv[1];
$info = parse_url($url);

if(!isset($info['host']) || !isset($info['path'])) {
    exit("Failed to parse host and path.\n");
}

if($info['host'] == '5.2.70.45') {
    $url = str_replace('5.2.70.45', 'phoenix:phoenix@5.2.70.45', $url);
}

if(substr($info['path'], -1) == '/') {
    $cmd = 'wget -cr -np -R "index.html*" "' . $url . '"';
} else {
    if($downloader == 'aria2c') {
        $cmd = $downloader . ' -x16 -s16 --file-allocation=none --show-console-readout=true "' . $url . '"';
        $cmd = 'stdbuf -o0 ' . $downloader . ' -x16 -s16 --file-allocation=none --continue=true --allow-overwrite=false --auto-file-renaming=false --show-console-readout=true "' . $url . '" 2>&1';
    } else {
        $cmd = $downloader . ' "' . $url . '"';
    }
}

ob_implicit_flush(true);
echo $cmd . "\n";
passthru($cmd);

?>