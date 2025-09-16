<?php

ini_set('display_errors',1);
ini_set('display_startup_errors',1);
error_reporting(-1);

if(!$NEWSBOAT_DB_FILE = getenv('NEWSBOAT_DB_FILE')) {
	exit('NEWSBOAT_DB_FILE env var is not set');
}

$db = new SQLite3($NEWSBOAT_DB_FILE, SQLITE3_OPEN_READWRITE);

$res = $db->query('SELECT author, title, url FROM rss_item WHERE deleted = 0 ORDER BY author, title ASC;');

while ($row = $res->fetchArray()) {
    //echo "{$row['id']} {$row['name']} {$row['price']} \n";
	//echo ($row['url']); echo "\n";

	extract($row);

	#echo "<a href='$url'>$author - $title</><br>\n";	
	echo "$url - $author - $title\n";
}



