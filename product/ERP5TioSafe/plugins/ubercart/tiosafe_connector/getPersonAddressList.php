<?php
include('database.php');
header('Content-Type: text/plain; charset=utf-8');
$sql = "SELECT order_id as id,  billing_street1 as street, billing_postal_code as zip,  billing_city as city, ";
$sql .= "country_name as country " ;
$sql .= "FROM uc_orders uco " ;
$sql .= "LEFT OUTER JOIN uc_countries ucc ON ucc.country_id = uco.billing_country ";
if (isset($_POST['id'])) {
    $sql .= " WHERE order_id=".$_POST['id']." ";
}
if (isset($_POST['person_id'])) {
    $sql .= " WHERE order_id=".$_POST['person_id']." ";
}
$sql .= "ORDER BY billing_city, billing_street1 ASC";
echo executeSQL($sql);
?>