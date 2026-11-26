@extends('layouts.app')
@section('title', 'Dashboard')
@section('content')
<h1>Users ({{ count($users) }})</h1>
<ul>
@forelse($users as $user)
  <li>{{ $user->name }} &lt;{{ $user['email'] }}&gt;</li>
@empty
  <li>none</li>
@endforelse
</ul>
@if($title !== null && $title)
<p>{!! $title !!}</p>
@else
<p>no title</p>
@endif
@endsection
