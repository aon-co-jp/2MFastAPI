<?php
namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;

class PhotoController extends Controller
{
    public function index()
    {
        return User::all();
    }

    public function show(User $photo)
    {
        return $photo;
    }

    public function store(Request $request)
    {
        $user = User::create(['name' => $request->input('name'), 'email' => $request->input('email', 'none')]);
        return response()->json($user, 201);
    }

    public function update(Request $request, $photo)
    {
        DB::table('users')->update($request->all());
        return 'ok';
    }
}
