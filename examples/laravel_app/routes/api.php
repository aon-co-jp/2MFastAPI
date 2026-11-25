<?php
use Illuminate\Support\Facades\Route;

Route::get('/users/{id}', function ($id) {
    return ['id' => $id, 'role' => 'member'];
});

Route::post('/orders', function (Request $request) {
    $o = Order::create($request->all());
    return $o;
});
