package eu.kanade.tachiyomi.extension.en.mangakakalot

import eu.kanade.tachiyomi.multisrc.mangabox.MangaBox
import okhttp3.Headers

class Mangakakalot : MangaBox("MangaKakalot", "https://www.mangakakalove.com", "en") {
    override fun headersBuilder(): Headers.Builder = super.headersBuilder().set("Referer", baseUrl)
    override val popularUrlPath = "manga-list/hot-manga?page="
    override val latestUrlPath = "manga-list/latest-manga?page="
    override val simpleQueryPath = "search/story/"
    override fun popularMangaSelector() = "div.list-comic-item-wrap, div.list-truyen-item-wrap, div.truyen-list > div.list-truyen-item-wrap"
    override fun searchMangaSelector() = "div.list-comic-item-wrap, div.list-truyen-item-wrap, div.search-story-item, .panel_story_list .story_item"
}

