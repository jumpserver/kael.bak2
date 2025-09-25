<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { marked } from 'marked';
	import Fuse from 'fuse.js';

	import { flyAndScale } from '$lib/utils/transitions';
	import { createEventDispatcher, onMount, getContext, tick } from 'svelte';

	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	import { deleteModel, getOllamaVersion, pullModel } from '$lib/apis/ollama';

	import {
		user,
		MODEL_DOWNLOAD_POOL,
		models,
		mobile,
		temporaryChatEnabled,
		settings,
		config
	} from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import { capitalizeFirstLetter, sanitizeResponseContent, splitStream } from '$lib/utils';
	import { getModels } from '$lib/apis';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import ChatBubbleOval from '$lib/components/icons/ChatBubbleOval.svelte';
	import { goto } from '$app/navigation';
	import ModelIcon from '$lib/components/icons/models/ModelIcon.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let id = '';
	export let value = '';
	export let placeholder = 'Select a model';
	export let searchEnabled = true;
	export let searchPlaceholder = $i18n.t('Search a model');

	export let showTemporaryChatControl = false;

	export let items: {
		label: string;
		value: string;
		model: Model;
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		[key: string]: any;
	}[] = [];

	export let className = 'w-[32rem]';
	export let triggerClassName = 'text-lg';

	let tagsContainerElement;

	let show = false;
	let tags = [];

	let selectedModel = '';
	$: selectedModel = items.find((item) => item.value === value) ?? '';

	let searchValue = '';

	let selectedTag = '';
	let selectedConnectionType = '';

	let ollamaVersion = null;
	let selectedModelIdx = 0;

	const fuse = new Fuse(
		items.map((item) => {
			const _item = {
				...item,
				modelName: item.model?.name,
				tags: (item.model?.tags ?? []).map((tag) => tag.name).join(' '),
				desc: item.model?.info?.meta?.description
			};
			return _item;
		}),
		{
			keys: ['value', 'tags', 'modelName'],
			threshold: 0.4
		}
	);

	$: filteredItems = (
		searchValue
			? fuse
					.search(searchValue)
					.map((e) => {
						return e.item;
					})
					.filter((item) => {
						if (selectedTag === '') {
							return true;
						}
						return (item.model?.tags ?? []).map((tag) => tag.name).includes(selectedTag);
					})
					.filter((item) => {
						if (selectedConnectionType === '') {
							return true;
						} else if (selectedConnectionType === 'ollama') {
							return item.model?.owned_by === 'ollama';
						} else if (selectedConnectionType === 'openai') {
							return item.model?.owned_by === 'openai';
						} else if (selectedConnectionType === 'direct') {
							return item.model?.direct;
						}
					})
			: items
					.filter((item) => {
						if (selectedTag === '') {
							return true;
						}
						return (item.model?.tags ?? []).map((tag) => tag.name).includes(selectedTag);
					})
					.filter((item) => {
						if (selectedConnectionType === '') {
							return true;
						} else if (selectedConnectionType === 'ollama') {
							return item.model?.owned_by === 'ollama';
						} else if (selectedConnectionType === 'openai') {
							return item.model?.owned_by === 'openai';
						} else if (selectedConnectionType === 'direct') {
							return item.model?.direct;
						}
					})
	).filter((item) => !(item.model?.info?.meta?.hidden ?? false));

	$: if (selectedTag || selectedConnectionType) {
		resetView();
	} else {
		resetView();
	}

	const resetView = async () => {
		await tick();

		const selectedInFiltered = filteredItems.findIndex((item) => item.value === value);

		if (selectedInFiltered >= 0) {
			// The selected model is visible in the current filter
			selectedModelIdx = selectedInFiltered;
		} else {
			// The selected model is not visible, default to first item in filtered list
			selectedModelIdx = 0;
		}

		await tick();
		const item = document.querySelector(`[data-arrow-selected="true"]`);
		item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => false);

		if (items) {
			tags = items
				.filter((item) => !(item.model?.info?.meta?.hidden ?? false))
				.flatMap((item) => item.model?.tags ?? [])
				.map((tag) => tag.name);

			// Remove duplicates and sort
			tags = Array.from(new Set(tags)).sort((a, b) => a.localeCompare(b));
		}
	});
</script>

<DropdownMenu.Root
	bind:open={show}
	onOpenChange={async () => {
		searchValue = '';
		window.setTimeout(() => document.getElementById('model-search-input')?.focus(), 0);

		resetView();
	}}
	closeFocus={false}
>
	<DropdownMenu.Trigger
		class="relative w-full font-primary"
		aria-label={placeholder}
		id="model-selector-{id}-button"
	>
		<div
			class="flex w-full text-left px-0.5 outline-hidden bg-transparent truncate {triggerClassName} justify-between font-medium placeholder-gray-400 focus:outline-hidden"
		>
			{#if selectedModel}
				{selectedModel.label.split('/').slice(-1)[0]}
			{:else}
				{placeholder}
			{/if}
			<ChevronDown className=" self-center ml-2 size-3" strokeWidth="2.5" />
		</div>
	</DropdownMenu.Trigger>

	<DropdownMenu.Content
		class=" z-40 {$mobile
			? `w-full`
			: `${className}`} max-w-[calc(100vw-1rem)] justify-start rounded-xl  bg-white dark:bg-gray-850 dark:text-white shadow-lg  outline-hidden"
		transition={flyAndScale}
		side={$mobile ? 'bottom' : 'bottom-start'}
		sideOffset={3}
	>
		<slot>
			{#if searchEnabled}
				<div class="flex items-center gap-2.5 px-5 mt-3.5 mb-1.5">
					<Search className="size-4" strokeWidth="2.5" />

					<input
						id="model-search-input"
						bind:value={searchValue}
						class="w-full text-sm bg-transparent outline-hidden"
						placeholder={searchPlaceholder}
						autocomplete="off"
						on:keydown={(e) => {
							if (e.code === 'Enter' && filteredItems.length > 0) {
								value = filteredItems[selectedModelIdx].value;
								show = false;
								return; // dont need to scroll on selection
							} else if (e.code === 'ArrowDown') {
								selectedModelIdx = Math.min(selectedModelIdx + 1, filteredItems.length - 1);
							} else if (e.code === 'ArrowUp') {
								selectedModelIdx = Math.max(selectedModelIdx - 1, 0);
							} else {
								// if the user types something, reset to the top selection.
								selectedModelIdx = 0;
							}

							const item = document.querySelector(`[data-arrow-selected="true"]`);
							item?.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
						}}
					/>
				</div>
			{/if}

			<div class="px-3 max-h-64 overflow-y-auto scrollbar-hidden group relative">
				{#if tags && items.filter((item) => !(item.model?.info?.meta?.hidden ?? false)).length > 0}
					<div
						class=" flex w-full sticky top-0 z-10 bg-white dark:bg-gray-850 overflow-x-auto scrollbar-none"
						on:wheel={(e) => {
							if (e.deltaY !== 0) {
								e.preventDefault();
								e.currentTarget.scrollLeft += e.deltaY;
							}
						}}
					>
						<div
							class="flex gap-1 w-fit text-center text-sm font-medium rounded-full bg-transparent px-1.5 pb-0.5"
							bind:this={tagsContainerElement}
						>
							{#if (items.find((item) => item.model?.owned_by === 'ollama') && items.find((item) => item.model?.owned_by === 'openai')) || items.find((item) => item.model?.direct) || tags.length > 0}
								<button
									class="min-w-fit outline-none p-1.5 {selectedTag === '' &&
									selectedConnectionType === ''
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition capitalize"
									on:click={() => {
										selectedConnectionType = '';
										selectedTag = '';
									}}
								>
									{$i18n.t('All')}
								</button>
							{/if}
							{#if items.find((item) => item.model?.direct)}
								<button
									class="min-w-fit outline-none p-1.5 {selectedConnectionType === 'direct'
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition capitalize"
									on:click={() => {
										selectedTag = '';
										selectedConnectionType = 'direct';
									}}
								>
									{$i18n.t('Direct')}
								</button>
							{/if}

							{#each tags as tag}
								<button
									class="min-w-fit outline-none p-1.5 {selectedTag === tag
										? ''
										: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition capitalize"
									on:click={() => {
										selectedConnectionType = '';
										selectedTag = tag;
									}}
								>
									{tag}
								</button>
							{/each}
						</div>
					</div>
				{/if}

				{#each filteredItems as item, index}
					<button
						aria-label="model-item"
						class="flex w-full text-left font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-hidden transition-all duration-75 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg cursor-pointer data-highlighted:bg-muted {index ===
						selectedModelIdx
							? 'bg-gray-100 dark:bg-gray-800 group-hover:bg-transparent'
							: ''}"
						data-arrow-selected={index === selectedModelIdx}
						data-value={item.value}
						on:click={() => {
							value = item.value;
							selectedModelIdx = index;

							show = false;
						}}
					>
						<div class="flex flex-col">
							{#if $mobile && (item?.model?.tags ?? []).length > 0}
								<div class="flex gap-0.5 self-start h-full mb-1.5 -translate-x-1">
									{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
										<div
											class=" text-xs font-bold px-1 rounded-sm uppercase line-clamp-1 bg-gray-500/20 text-gray-700 dark:text-gray-200"
										>
											{tag.name}
										</div>
									{/each}
								</div>
							{/if}
							<div class="flex items-center gap-2">
								<div class="flex items-center min-w-fit">
									<div class="line-clamp-1">
										<div class="flex items-center min-w-fit" style="display: hidden;">
											<Tooltip
												content={$user?.role === 'admin' ? (item?.value ?? '') : ''}
												placement="top-start"
											>
												{#if item.model?.name ?? item.value ?? item.label ?? ''}
													<ModelIcon
														name={item.model?.name ?? item.value ?? item.label ?? ''}
														className="size-5 mr-2"
													/>
												{:else}
													<img
														src={item.model?.info?.meta?.profile_image_url ?? '/user.png'}
														alt="Model"
														class="rounded-full size-5 flex items-center mr-2"
													/>
												{/if}

												<div class="flex items-center line-clamp-1">
													<div class="line-clamp-1">
														{item.label}
													</div>

													{#if item.model.owned_by === 'ollama' && (item.model.ollama?.details?.parameter_size ?? '') !== ''}
														<div class="flex ml-1 items-center translate-y-[0.5px]">
															<Tooltip
																content={`${
																	item.model.ollama?.details?.quantization_level
																		? item.model.ollama?.details?.quantization_level + ' '
																		: ''
																}${
																	item.model.ollama?.size
																		? `(${(item.model.ollama?.size / 1024 ** 3).toFixed(1)}GB)`
																		: ''
																}`}
																className="self-end"
															>
																<span
																	class=" text-xs font-medium text-gray-600 dark:text-gray-400 line-clamp-1"
																	>{item.model.ollama?.details?.parameter_size ?? ''}</span
																>
															</Tooltip>
														</div>
													{/if}
												</div>
											</Tooltip>
										</div>
									</div>
								</div>

								<!-- {JSON.stringify(item.info)} -->
								{#if !$mobile && (item?.model?.tags ?? []).length > 0}
									<div
										class="flex gap-0.5 self-center items-center h-full translate-y-[0.5px] overflow-x-auto scrollbar-none"
									>
										{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
											<Tooltip content={tag.name} className="flex-shrink-0">
												<div
													class=" text-xs font-bold px-1 rounded-sm uppercase bg-gray-500/20 text-gray-700 dark:text-gray-200"
												>
													{tag.name}
												</div>
											</Tooltip>
										{/each}
									</div>
								{/if}
							</div>
						</div>

						{#if value === item.value}
							<div class="ml-auto pl-2 pr-2 md:pr-0">
								<Check />
							</div>
						{/if}
					</button>
				{:else}
					<div class="">
						<div class="block px-3 py-2 text-sm text-gray-700 dark:text-gray-100">
							{$i18n.t('No results found')}
						</div>
					</div>
				{/each}
			</div>

			<div class="mb-3"></div>
			<div class="hidden w-[42rem]" />
			<div class="hidden w-[32rem]" />
		</slot>
	</DropdownMenu.Content>
</DropdownMenu.Root>
