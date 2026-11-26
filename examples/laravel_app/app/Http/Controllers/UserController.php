<?php
namespace App\Http\Controllers;

class UserController extends Controller
{
    public function index()
    {
        return ['users' => 'all'];
    }

    public function show($id)
    {
        return "User $id";
    }

    public function store(Request $request)
    {
        return User::create($request->all());
    }
}
