package eu.kanade.tachiyomi.extension.en.webtoons

import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.network.asObservableSuccess
import eu.kanade.tachiyomi.source.model.FilterList
import eu.kanade.tachiyomi.source.model.MangasPage
import eu.kanade.tachiyomi.source.model.Page
import eu.kanade.tachiyomi.source.model.SChapter
import eu.kanade.tachiyomi.source.model.SManga
import eu.kanade.tachiyomi.source.online.ParsedHttpSource
import eu.kanade.tachiyomi.util.asJsoup
import okhttp3.Headers
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import org.json.JSONObject
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element
import org.jsoup.parser.Parser
import rx.Observable
import java.net.SocketException
import java.text.DecimalFormat
import java.util.Calendar
import java.util.concurrent.TimeUnit

class Webtoons : ParsedHttpSource() {

    override val name = "Webtoons.com"

    override val baseUrl = "https://www.webtoons.com"

    private val mobileUrl = "https://m.webtoons.com"

    override val lang = "en"

    override val supportsLatest = true

    override val client: OkHttpClient = network.cloudflareClient.newBuilder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val req = chain.request()
            val newReq = if (req.url.host.contains("webtoons.com")) {
                req.newBuilder()
                    .header("Cookie", "ageGatePass=true; locale=en; needGDPR=false")
                    .build()
            } else {
                req
            }
            try {
                chain.proceed(newReq)
            } catch (e: SocketException) {
                chain.proceed(newReq)
            }
        }
        .build()

    override fun headersBuilder(): Headers.Builder = super.headersBuilder()
        .add("Referer", "$baseUrl/")

    private val mobileHeaders: Headers
        get() = headersBuilder()
            .set("Referer", "$mobileUrl/")
            .removeAll("Origin")
            .build()

    // Popular
    override fun popularMangaRequest(page: Int): Request {
        val ranking = when (page) {
            1 -> "trending"
            2 -> "popular"
            3 -> "canvas"
            else -> "popular"
        }
        return GET("$baseUrl/en/ranking/$ranking", headers)
    }

    override fun popularMangaSelector(): String = ".webtoon_list li a"

    override fun popularMangaFromElement(element: Element): SManga = SManga.create().apply {
        setUrlWithoutDomain(element.absUrl("href"))
        title = element.selectFirst(".title")?.text() ?: ""
        thumbnail_url = element.selectFirst("img")?.absUrl("src")
    }

    override fun popularMangaNextPageSelector(): String? = null

    // Latest
    override fun latestUpdatesRequest(page: Int): Request {
        val day = when (Calendar.getInstance().get(Calendar.DAY_OF_WEEK)) {
            Calendar.MONDAY -> "monday"
            Calendar.TUESDAY -> "tuesday"
            Calendar.WEDNESDAY -> "wednesday"
            Calendar.THURSDAY -> "thursday"
            Calendar.FRIDAY -> "friday"
            Calendar.SATURDAY -> "saturday"
            Calendar.SUNDAY -> "sunday"
            else -> "monday"
        }
        return GET("$baseUrl/en/originals/$day?sortOrder=UPDATE", headers)
    }

    override fun latestUpdatesSelector(): String = popularMangaSelector()

    override fun latestUpdatesFromElement(element: Element): SManga = popularMangaFromElement(element)

    override fun latestUpdatesNextPageSelector(): String? = null

    // Search
    override fun searchMangaRequest(page: Int, query: String, filters: FilterList): Request {
        val url = "$baseUrl/en/search".toHttpUrl().newBuilder()
            .addQueryParameter("keyword", query)
        if (page > 1) {
            url.addQueryParameter("page", page.toString())
        }
        return GET(url.build().toString(), headers)
    }

    override fun searchMangaSelector(): String = ".webtoon_list li a"

    override fun searchMangaFromElement(element: Element): SManga = popularMangaFromElement(element)

    override fun searchMangaNextPageSelector(): String = "a.pagination[aria-current=true] + a"

    // Details
    override fun mangaDetailsParse(document: Document): SManga = SManga.create().apply {
        val detailElement = document.selectFirst(".detail_header .info")
        val infoElement = document.selectFirst("#_asideDetail")

        title = document.selectFirst("h1.subj, h3.subj")?.text() ?: ""
        author = detailElement?.selectFirst(".author:nth-of-type(1)")?.ownText()
            ?: detailElement?.selectFirst(".author_area")?.ownText() ?: ""
        artist = detailElement?.selectFirst(".author:nth-of-type(2)")?.ownText()
            ?: detailElement?.selectFirst(".author_area")?.ownText() ?: author
        genre = detailElement?.select(".genre").orEmpty().joinToString { it.text() }
        description = infoElement?.selectFirst("p.summary")?.text() ?: ""
        status = with(infoElement?.selectFirst("p.day_info")?.text().orEmpty()) {
            when {
                contains("UP") || contains("EVERY") -> SManga.ONGOING
                contains("END") || contains("COMPLETED") -> SManga.COMPLETED
                else -> SManga.UNKNOWN
            }
        }
        thumbnail_url = document.selectFirst("head meta[property=\"og:image\"]")?.attr("content")
    }

    // Chapters
    override fun chapterListSelector(): String = throw UnsupportedOperationException("Not used")

    override fun chapterFromElement(element: Element): SChapter = throw UnsupportedOperationException("Not used")

    override fun fetchChapterList(manga: SManga): Observable<List<SChapter>> {
        val webtoonUrl = (baseUrl + manga.url).toHttpUrl()
        val titleId = webtoonUrl.queryParameter("title_no")
            ?: webtoonUrl.queryParameter("titleNo")
            ?: throw Exception("Invalid webtoon url: ${manga.url}")

        val type = if (manga.url.contains("challenge") || manga.url.contains("canvas")) {
            "canvas"
        } else {
            "webtoon"
        }

        val url = "$mobileUrl/api/v1/$type/$titleId/episodes?pageSize=99999".toHttpUrl().newBuilder().apply {
            if (type == "canvas") {
                addQueryParameter("readingLanguageCode", "en")
            }
        }.build()

        return client.newCall(GET(url.toString(), mobileHeaders))
            .asObservableSuccess()
            .map { response ->
                chapterListParse(response)
            }
    }

    private fun chapterListParse(response: Response): List<SChapter> {
        val json = JSONObject(response.body?.string().orEmpty())
        val result = json.optJSONObject("result") ?: return emptyList()
        val episodes = result.optJSONArray("episodeList") ?: return emptyList()

        val chapters = ArrayList<SChapter>(episodes.length())
        val numberFormatter = DecimalFormat("#.##")

        for (i in 0 until episodes.length()) {
            val ep = episodes.getJSONObject(i)
            val chapter = SChapter.create().apply {
                url = ep.optString("viewerLink")
                val epTitle = ep.optString("episodeTitle")
                val epNo = ep.optInt("episodeNo", i + 1)
                chapter_number = epNo.toFloat()
                name = "${Parser.unescapeEntities(epTitle, false)} (ch. ${numberFormatter.format(chapter_number)})"
                date_upload = ep.optLong("exposureDateMillis", 0L)
            }
            chapters.add(chapter)
        }
        return chapters.reversed()
    }

    // Pages
    override fun pageListParse(document: Document): List<Page> {
        return document.select("div#_imageList img").mapIndexed { i, element ->
            val dataUrl = element.attr("data-url").ifEmpty { element.attr("src") }
            Page(i, imageUrl = dataUrl)
        }
    }

    override fun imageUrlParse(document: Document): String = throw UnsupportedOperationException("Not used")
}
