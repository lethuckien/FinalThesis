<?php

    



    $servername = "localhost";
    $username = "root";
    $password = "1";
    $database = 'test';
    // Create connection
    $conn = new mysqli($servername, $username, $password, $database);
    
    // Check connection
    if ($conn->connect_error) {
      die("Connection failed");
    }
    $query = $_GET['query'];
    $query_type = $_GET['query_type'];
    if (isset($query)){
        $result = $conn->query($query);
        if ($result){
            if ($query_type == 'select' || $query_type == 'count'){
                $r = '[';
                while($row = $result->fetch_assoc()){
                    $r .= json_encode($row);
                    $r .= ',';
                }
                echo rtrim($r,',').']';
            }
            elseif ($query_type == 'insert'){
                echo mysqli_insert_id($conn);
            }
        }
        else {
            echo mysqli_error($conn);
        }
    }
    $conn->close();
?>