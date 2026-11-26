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

    public function update(Request $request, User $photo)
    {
        $data = $request->validate(['name' => 'required|string|max:20', 'email' => ['nullable', 'email']]);
        $photo->update($data);
        return $photo;
    }

    public function destroy($photo)
    {
        User::destroy($photo);
        return response()->json(['deleted' => $photo], 200);
    }

    public function edit(Request $request, $photo)
    {
        $request->file('avatar')->store('a');
        return 'never';
    }
}
