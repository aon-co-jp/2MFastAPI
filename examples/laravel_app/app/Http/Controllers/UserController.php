<?php
namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;

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
