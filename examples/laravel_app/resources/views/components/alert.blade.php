@props(['type' => 'info'])
<div class="alert alert-{{ $type }}">@if($title ?? false)<b>{{ $title }}</b> @endif{{ $slot }}</div>
