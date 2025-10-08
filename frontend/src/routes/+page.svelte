<script lang="ts">
    import SidePanel from '$lib/components/SidePanel.svelte';
    import type { PageData } from './$types';
    export let data: PageData;
</script>
<SidePanel {data} />


<!-- <style>
    .new-study-button {
        padding: 10px 15px;
        background-color: #007bff;
        color: white;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-size: 1em;
        margin-bottom: 20px;
    }
    .new-study-button:hover {
        background-color: #0056b3;
    }
    ul { list-style: none; padding: 0; }
    li { margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }
    a { text-decoration: none; color: inherit; display: block; padding: 5px; }
    a:hover { background-color: #f0f0f0; }
    .empty-state {
        color: #888;
        padding-top: 20px;
        text-align: center;
    }
</style> -->