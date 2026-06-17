APP_STYLE = """
* {
    font-family: "Times New Roman";
}

QMainWindow {
    background-color: #1f2d35;
}

QWidget#RootWidget {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1f2d35,
        stop:0.45 #2f4548,
        stop:1 #5d6f63
    );
}

QWidget#Card {
    background-color: rgba(239, 235, 222, 225);
    border: 2px solid rgba(214, 205, 184, 190);
    border-radius: 18px;
}

QWidget#SoftBlueCard {
    background-color: rgba(213, 229, 229, 220);
    border: 2px solid rgba(180, 203, 202, 190);
    border-radius: 18px;
}

QWidget#DarkCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #24394a,
        stop:1 #4d6d76
    );
    border: 2px solid rgba(178, 200, 196, 170);
    border-radius: 18px;
}

QWidget#DateCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #f4c47a,
        stop:0.48 #e7d3a6,
        stop:1 #d6e1d3
    );
    border: 2px solid rgba(235, 214, 166, 210);
    border-radius: 20px;
}

QWidget#StocksCard {
    background-color: rgba(37, 54, 63, 230);
    border: 2px solid rgba(144, 169, 166, 170);
    border-radius: 18px;
}

QWidget#WeatherRow {
    background-color: rgba(239, 235, 222, 215);
    border: 2px solid rgba(214, 205, 184, 170);
    border-radius: 15px;
}

QWidget#WeatherRowNow {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #f4c47a,
        stop:1 #e9d7b6
    );
    border: 2px solid #e8c477;
    border-radius: 15px;
}

QWidget#ImagePlaceholderLight {
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #cadbdf,
        stop:0.55 #e2e1cf,
        stop:1 #e4c8a9
    );
    border: 2px solid rgba(173, 196, 192, 190);
    border-radius: 14px;
}

QWidget#ImagePlaceholderDark {
    background-color: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0 #253f55,
        stop:0.6 #416a78,
        stop:1 #879b82
    );
    border: 2px solid rgba(169, 190, 192, 170);
    border-radius: 14px;
}

QWidget#StockRow {
    background-color: rgba(255, 248, 230, 35);
    border: 1px solid rgba(197, 213, 207, 70);
    border-radius: 12px;
}

QWidget#IndexMiniCard {
    background-color: rgba(255, 248, 230, 42);
    border: 1px solid rgba(197, 213, 207, 80);
    border-radius: 12px;
}

QWidget#StockGainPill {
    background-color: rgba(98, 151, 108, 80);
    border: 1px solid rgba(148, 201, 157, 120);
    border-radius: 8px;
}

QWidget#StockLossPill {
    background-color: rgba(170, 93, 93, 80);
    border: 1px solid rgba(210, 145, 145, 120);
    border-radius: 8px;
}

QWidget#TodayReminderRow {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #efd9a0,
        stop:1 #efe8d8
    );
    border: 1px solid #d3b86b;
    border-radius: 12px;
}

QWidget#NewspaperSportsCard {
    background-color: rgba(247, 241, 229, 240);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#PaperFeaturedStory {
    background-color: rgba(255, 250, 241, 150);
    border: 1px solid rgba(155, 137, 112, 110);
    border-radius: 8px;
}

QWidget#PaperStory {
    background-color: rgba(255, 252, 247, 110);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#ScoreboardCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #17262d,
        stop:0.48 #263c3f,
        stop:1 #3f5146
    );
    border: 2px solid rgba(160, 190, 185, 150);
    border-radius: 16px;
}

QWidget#LeagueScoreboard {
    background-color: rgba(8, 18, 22, 95);
    border: 1px solid rgba(170, 205, 195, 100);
    border-radius: 12px;
}

QWidget#ScoreboardGameTile {
    background-color: rgba(245, 235, 196, 28);
    border: 1px solid rgba(245, 235, 196, 70);
    border-radius: 9px;
}

QWidget#NewspaperGamesCard {
    background-color: rgba(247, 241, 229, 235);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#PaperLeagueColumn {
    background-color: rgba(255, 252, 247, 95);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#PaperGameListing {
    background-color: rgba(255, 250, 241, 120);
    border: 1px solid rgba(155, 137, 112, 80);
    border-radius: 7px;
}

QLabel#PaperGamesMasthead {
    font-size: 24px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#PaperGamesEdition {
    font-size: 9px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperScheduleTag {
    font-size: 9px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #7a5f43;
    border-radius: 8px;
    padding: 3px;
}

QLabel#PaperLeagueTitle {
    font-size: 20px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#PaperGameTime {
    font-size: 9px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperGameMatchup {
    font-size: 28px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#PaperGameDetail {
    font-size: 10px;
    font-weight: 500;
    color: #5b5045;
}

QWidget#CleanGamesCard {
    background-color: rgba(247, 241, 229, 235);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 14px;
}

QWidget#CleanGameCard {
    background-color: rgba(255, 250, 241, 125);
    border: 1px solid rgba(155, 137, 112, 90);
    border-radius: 8px;
}

QLabel#CleanGamesTitle {
    font-size: 22px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#CleanGamesSubtitle {
    font-size: 9px;
    font-weight: 900;
    color: #7a5f43;
    letter-spacing: 1px;
}

QLabel#CleanLeagueTitle {
    font-size: 22px;
    font-weight: 900;
    color: #2f2a24;
}

QLabel#CleanGameTime {
    font-size: 10px;
    font-weight: 900;
    color: #9a4d3d;
}

QLabel#CleanGameMatchup {
    font-size: 28px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#CleanGameDetail {
    font-size: 10px;
    font-weight: 600;
    color: #5b5045;
}

QWidget#GameDayCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #efe6d2,
        stop:1 #d9c8a8
    );
    border: 2px solid rgba(126, 103, 76, 170);
    border-radius: 14px;
}

QWidget#GameDayLeagueCard {
    background-color: rgba(255, 250, 239, 135);
    border: 1px solid rgba(116, 95, 70, 120);
    border-radius: 10px;
}

QWidget#GameDayMatchupBox {
    background-color: rgba(45, 58, 62, 210);
    border: 1px solid rgba(230, 210, 160, 130);
    border-radius: 8px;
}

QLabel#GameDayTitle {
    font-size: 24px;
    font-weight: 900;
    color: #2d2a24;
    letter-spacing: 1px;
}

QLabel#GameDaySubtitle {
    font-size: 10px;
    font-weight: 900;
    color: #735d3f;
    letter-spacing: 1px;
}

QLabel#GameDayLeague {
    font-size: 22px;
    font-weight: 900;
    color: #2d2a24;
}

QLabel#GameDayTime {
    font-size: 10px;
    font-weight: 900;
    color: #e9c46a;
}

QLabel#GameDayMatchup {
    font-size: 28px;
    font-weight: 900;
    color: #fff8e8;
}

QLabel#GameDayDetail {
    font-size: 9px;
    font-weight: 700;
    color: #cfd8d3;
}

QWidget#MarketTapeCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #17262d,
        stop:0.50 #22383b,
        stop:1 #3c4939
    );
    border: 2px solid rgba(205, 184, 125, 145);
    border-radius: 15px;
}

QWidget#MarketTapeIndexCard {
    background-color: rgba(245, 232, 181, 32);
    border: 1px solid rgba(231, 205, 132, 95);
    border-radius: 9px;
}

QWidget#MarketTapeStockTile {
    background-color: rgba(7, 17, 21, 115);
    border: 1px solid rgba(180, 205, 190, 80);
    border-radius: 10px;
}

QLabel#MarketTapeTitle {
    font-size: 18px;
    font-weight: 900;
    color: #f2e5b8;
    letter-spacing: 1px;
}

QLabel#MarketTapeSubtitle {
    font-size: 8px;
    font-weight: 800;
    color: #b7c7bd;
    letter-spacing: 1px;
}

QLabel#MarketTapeBadge {
    font-size: 9px;
    font-weight: 900;
    color: #1a272c;
    background-color: #e2c66f;
    border-radius: 9px;
    padding: 3px;
}

QLabel#MarketTapeSectionLabel {
    font-size: 8px;
    font-weight: 900;
    color: #d9c98f;
    letter-spacing: 1px;
}

QLabel#MarketTapeIndexName {
    font-size: 9px;
    font-weight: 900;
    color: #d9c98f;
    letter-spacing: 1px;
}

QLabel#MarketTapeIndexPrice {
    font-size: 16px;
    font-weight: 900;
    color: #f7f1dc;
}

QLabel#MarketTapePrice {
    font-size: 15px;
    font-weight: 900;
    color: #f7f1dc;
}

QWidget#MarketTapeAHBox {
    background-color: rgba(255, 255, 255, 18);
    border: 1px solid rgba(255, 255, 255, 38);
    border-radius: 8px;
}

QLabel#MarketTapeAHLabel {
    font-size: 7px;
    font-weight: 900;
    color: #c6d3cc;
    letter-spacing: 1px;
}

QWidget#RemindersCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #f1ead9,
        stop:1 #d8c9ac
    );
    border: 2px solid rgba(126, 103, 76, 150);
    border-radius: 14px;
}

QLabel#RemindersTitle {
    font-size: 18px;
    font-weight: 900;
    color: #2d2a24;
    letter-spacing: 1px;
}

QLabel#ReminderTodayBadge {
    font-size: 9px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #8e5f45;
    border-radius: 9px;
    padding: 3px;
}

QLabel#TodayReminderGroupTitle {
    font-size: 9px;
    font-weight: 900;
    color: #8e5f45;
    letter-spacing: 1px;
}

QLabel#UpcomingReminderGroupTitle {
    font-size: 8px;
    font-weight: 900;
    color: rgba(74, 62, 48, 155);
    letter-spacing: 1px;
}

QWidget#TodayReminderRow {
    background-color: rgba(255, 248, 234, 190);
    border: 2px solid rgba(142, 95, 69, 125);
    border-radius: 11px;
}

QWidget#UpcomingReminderRow {
    background-color: rgba(255, 250, 240, 80);
    border: 1px solid rgba(116, 95, 70, 70);
    border-radius: 8px;
}

QLabel#TodayReminderIcon {
    font-size: 20px;
}

QLabel#UpcomingReminderIcon {
    font-size: 13px;
    color: rgba(74, 62, 48, 150);
}

QLabel#TodayReminderText {
    font-size: 16px;
    font-weight: 900;
    color: #2d2a24;
}

QLabel#UpcomingReminderText {
    font-size: 10px;
    font-weight: 700;
    color: rgba(47, 42, 36, 165);
}

QWidget#FoxNewsCard {
    background-color: rgba(239, 232, 217, 245);
    border: 2px solid rgba(173, 147, 118, 150);
    border-radius: 18px;
}

QWidget#CnbcNewsCard {
    background-color: rgba(225, 234, 229, 245);
    border: 2px solid rgba(116, 152, 151, 150);
    border-radius: 18px;
}

QWidget#FoxNewsTextPanel {
    background-color: rgba(247, 241, 229, 245);
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
}

QWidget#CnbcNewsTextPanel {
    background-color: rgba(232, 238, 232, 245);
    border-bottom-left-radius: 18px;
    border-bottom-right-radius: 18px;
}

QLabel#FoxSourcePill {
    font-size: 10px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b56a58;
    border-radius: 8px;
    padding: 4px 10px;
}

QLabel#CnbcSourcePill {
    font-size: 10px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #4f89a0;
    border-radius: 8px;
    padding: 4px 10px;
}

QLabel#FoxNewsKicker {
    font-size: 8px;
    font-weight: 900;
    color: #8a5e4b;
    letter-spacing: 1px;
}

QLabel#CnbcNewsKicker {
    font-size: 8px;
    font-weight: 900;
    color: #54747d;
    letter-spacing: 1px;
}

QLabel#FoxHeadlineText {
    font-size: 21px;
    font-weight: 900;
    color: #24323b;
    line-height: 1.1em;
}

QLabel#CnbcHeadlineText {
    font-size: 21px;
    font-weight: 900;
    color: #24323b;
    line-height: 1.1em;
}

QLabel#NewsPaperMasthead {
    font-size: 27px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#NewsPaperEdition {
    font-size: 9px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#NewsPaperKicker {
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#NewsPaperHeadline {
    font-size: 23px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#NewsPaperFooter {
    font-size: 8px;
    font-weight: 700;
    color: #7a6d5c;
}

QLabel#MarketTapeUp {
    font-size: 11px;
    font-weight: 900;
    color: #eaf6df;
    background-color: rgba(86, 133, 91, 130);
    border-radius: 6px;
    padding: 1px;
}

QLabel#MarketTapeDown {
    font-size: 11px;
    font-weight: 900;
    color: #fff0ea;
    background-color: rgba(139, 75, 68, 130);
    border-radius: 6px;
    padding: 1px;
}

QLabel#MarketTapeTicker {
    font-size: 13px;
    font-weight: 900;
    color: #f7f1dc;
    letter-spacing: 1px;
}

QLabel#ScoreboardMainTitle {
    font-size: 14px;
    font-weight: 900;
    color: #e8f1dd;
    letter-spacing: 1px;
}

QLabel#ScoreboardStatusBadge {
    font-size: 10px;
    font-weight: 900;
    color: #17262d;
    background-color: #e5d08d;
    border-radius: 9px;
    padding: 3px;
}

QLabel#ScoreboardLeagueTitle {
    font-size: 22px;
    font-weight: 900;
    color: #f4e7ad;
    letter-spacing: 1px;
}

QLabel#ScoreboardLight {
    font-size: 10px;
    font-weight: 900;
    color: #f1c76a;
}

QLabel#ScoreboardMatchup {
    font-size: 12px;
    font-weight: 900;
    color: #f1f6ec;
}

QLabel#ScoreboardTimeBadge {
    font-size: 10px;
    font-weight: 900;
    color: #17262d;
    background-color: #b6d4c8;
    border-radius: 7px;
    padding: 2px;
}

QLabel#ScoreboardDetail {
    font-size: 9px;
    font-weight: 700;
    color: #c7d7cd;
}

QLabel#PaperMasthead {
    font-size: 25px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#PaperEditionLine {
    font-size: 9px;
    font-weight: 700;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperKicker {
    font-size: 8px;
    font-weight: 900;
    color: #7a5f43;
    letter-spacing: 1px;
}

QLabel#PaperKickerFeatured {
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperHeadlineFeatured {
    font-size: 20px;
    font-weight: 900;
    color: #2b2621;
    line-height: 1.05em;
}

QWidget#NewspaperNewsCard {
    background-color: rgba(247, 241, 229, 240);
    border: 2px solid rgba(166, 149, 122, 170);
    border-radius: 15px;
}

QWidget#NewsPaperPhotoBox {
    background-color: rgba(255, 250, 241, 150);
    border: 1px solid rgba(117, 97, 72, 130);
    border-radius: 10px;
}

QWidget#NewsPaperStoryPanel {
    background-color: rgba(255, 252, 247, 125);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 10px;
}

QLabel#OldNewsSourceName {
    font-size: 25px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#OldNewsEditionSmall {
    font-size: 8px;
    font-weight: 900;
    color: #7a6d5c;
    letter-spacing: 1px;
}

QLabel#OldNewsHeadline {
    font-size: 22px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#OldNewsFooter {
    font-size: 8px;
    font-weight: 800;
    color: #8b4e3f;
    letter-spacing: 1px;
}

QLabel#OldNewsPageNumber {
    font-size: 8px;
    font-weight: 900;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#OldNewsTopMasthead {
    font-size: 22px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#OldNewsKicker {
    font-size: 10px;
    font-weight: 900;
    color: #8b4e3f;
    letter-spacing: 2px;
}

QWidget#PaperFeaturedStory {
    background-color: rgba(255, 250, 241, 150);
    border: 1px solid rgba(155, 137, 112, 110);
    border-radius: 8px;
}

QWidget#PaperStory {
    background-color: rgba(255, 252, 247, 110);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#PaperLeagueColumn {
    background-color: rgba(255, 252, 247, 110);
    border: 1px solid rgba(155, 137, 112, 95);
    border-radius: 8px;
}

QWidget#PaperGameListing {
    background-color: rgba(255, 250, 241, 125);
    border: 1px solid rgba(155, 137, 112, 75);
    border-radius: 7px;
}

QLabel#PaperHeadline {
    font-size: 11px;
    font-weight: 700;
    color: #2f2a24;
    line-height: 1.1em;
}

QLabel#PaperLeagueTitle {
    font-size: 18px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 1px;
}

QLabel#PaperGameTime {
    font-size: 8px;
    font-weight: 900;
    color: #9a4d3d;
    letter-spacing: 1px;
}

QLabel#PaperGameMatchup {
    font-size: 11px;
    font-weight: 900;
    color: #2b2621;
}

QLabel#PaperGameDetail {
    font-size: 8px;
    font-weight: 600;
    color: #5b5045;
}

QLabel#PaperFooterLeft {
    font-size: 8px;
    font-weight: 800;
    color: #7a6d5c;
    letter-spacing: 1px;
}

QLabel#PaperFooterPage {
    font-size: 8px;
    font-weight: 900;
    color: #6b5f50;
    letter-spacing: 1px;
}

QLabel#PaperLeagueEmoji {
    font-size: 16px;
}

QWidget#PaperGameListingEmpty {
    background-color: rgba(255, 250, 241, 55);
    border: 1px dashed rgba(155, 137, 112, 70);
    border-radius: 7px;
}

QLabel#PaperGameTimeEmpty {
    font-size: 8px;
    font-weight: 900;
    color: rgba(90, 78, 63, 115);
    letter-spacing: 1px;
}

QLabel#PaperGameMatchupEmpty {
    font-size: 9px;
    font-weight: 700;
    color: rgba(47, 42, 36, 125);
}

QLabel#PaperGameDetailEmpty {
    font-size: 7px;
    font-weight: 600;
    color: rgba(91, 80, 69, 105);
}

QLabel#OldNewsReadLink {
    font-size: 8px;
    font-weight: 900;
    color: #8b4e3f;
    letter-spacing: 1px;
}

QLabel#DateWeatherTemp {
    font-size: 18px;
    font-weight: 900;
    color: #f8ead2;
    letter-spacing: 1px;
}

QLabel#DateWeatherHour {
    font-size: 10px;
    font-weight: 900;
    color: rgba(248, 234, 210, 190);
    letter-spacing: 1px;
}

QWidget#DateCardWeatherOverlay {
    background-color: transparent;
    border: none;
}

QWidget#DateWeatherBackground {
    border-radius: 14px;
}

QLabel#DateDayWeather {
    font-size: 36px;
    font-weight: 900;
    letter-spacing: 1px;
}

QLabel#DateMonthWeather {
    font-size: 18px;
    font-weight: 900;
}

QLabel#DateNumberWeather {
    font-size: 58px;
    font-weight: 900;
}

QLabel#DateCurrentWeather {
    font-size: 30px;
    font-weight: 900;
    letter-spacing: 1px;
}

QLabel#DateSubtitleWeather {
    font-size: 9px;
    font-weight: 900;
    letter-spacing: 1px;
}

QPushButton#UpcomingReminderSendButton {
    background-color: rgba(114, 84, 45, 0.54);
    color: rgba(247, 240, 223, 0.88);
    border: 1px solid rgba(77, 53, 27, 0.46);
    border-radius: 7px;
    padding: 1px 4px;
    font-size: 8px;
    font-weight: 900;
}

QPushButton#UpcomingReminderSendButton:hover {
    background-color: rgba(114, 84, 45, 0.72);
    color: rgba(247, 240, 223, 0.96);
    border: 1px solid rgba(77, 53, 27, 0.62);
}

QPushButton#UpcomingReminderSendButton:pressed {
    background-color: rgba(92, 67, 36, 0.82);
    color: rgba(247, 240, 223, 1.0);
}

QPushButton#ReminderSendButton {
    background-color: rgba(92, 74, 52, 210);
    color: #fff8ec;
    border: 1px solid rgba(55, 43, 30, 180);
    border-radius: 7px;
    padding: 3px 6px;
    font-size: 9px;
    font-weight: 900;
}

QPushButton#ReminderSendButton:hover {
    background-color: rgba(120, 94, 62, 230);
}

QPushButton#ReminderSendButton:pressed {
    background-color: rgba(72, 55, 37, 240);
}

QLabel#PaperNote {
    font-size: 10px;
    font-weight: 500;
    color: #40372e;
    line-height: 1.1em;
}

QWidget#UpcomingReminderRow {
    background-color: rgba(255, 248, 230, 70);
    border: 1px solid rgba(214, 205, 184, 110);
    border-radius: 9px;
}

QWidget#TodayReminderRow {
    background-color: rgba(239, 217, 160, 150);
    border: 1px solid rgba(211, 184, 107, 170);
    border-radius: 9px;
}

QWidget#SportsCreativeCard {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(214, 229, 229, 230),
        stop:0.48 rgba(239, 235, 222, 225),
        stop:1 rgba(225, 210, 183, 220)
    );
    border: 2px solid rgba(180, 203, 202, 190);
    border-radius: 18px;
}

QLabel#SportsCreativeTitle {
    font-size: 28px;
    font-weight: 900;
    color: #25313b;
}

QLabel#SportsCreativeSubtitle {
    font-size: 11px;
    font-weight: 900;
    color: #6f807a;
    letter-spacing: 1px;
}

QLabel#SportsLiveBadge {
    font-size: 11px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b76e5f;
    border: 1px solid rgba(255, 248, 236, 120);
    border-radius: 12px;
    padding: 3px;
}

QWidget#FeaturedSportsStory {
    background-color: rgba(255, 248, 230, 145);
    border: 1px solid rgba(183, 110, 95, 130);
    border-radius: 12px;
}

QWidget#SportsStoryRow {
    background-color: rgba(255, 248, 230, 85);
    border: 1px solid rgba(214, 205, 184, 110);
    border-radius: 10px;
}

QLabel#SportsNumberBadge {
    font-size: 12px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #6f807a;
    border-radius: 9px;
}

QLabel#FeaturedSportsNumberBadge {
    font-size: 13px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b76e5f;
    border-radius: 9px;
}

QLabel#SportsHeadline {
    font-size: 16px;
    font-weight: 600;
    color: #35434d;
}

QLabel#ReminderGroupTitle {
    font-size: 16px;
    font-weight: 900;
    color: #6f807a;
    letter-spacing: 1px;
}

QLabel#SectionTitle {
    font-size: 37px;
    font-weight: 900;
    color: #25313b;
}

QLabel#StockTicker {
    font-size: 15px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel#StockPrice {
    font-size: 25px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#StockUp {
    font-size: 12px;
    font-weight: 900;
    color: #a8d5a2;
}

QLabel#StockDown {
    font-size: 12px;
    font-weight: 900;
    color: #e0a2a2;
}

QLabel#IndexPrice {
    font-size: 19px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#IndexName {
    font-size: 12px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel {
    font-family: "Times New Roman";
    color: #263238;
}

QLabel#DateDay {
    font-size: 56px;
    font-weight: 900;
    color: #25313b;
}

QLabel#DateMonth {
    font-size: 24px;
    font-weight: 900;
    color: #4a5b58;
}

QLabel#DateNumber {
    font-size: 72px;
    font-weight: 900;
    color: #25313b;
}

QLabel#DateSubtitle {
    font-size: 12px;
    font-weight: 900;
    color: #6f7463;
    letter-spacing: 1px;
}

QLabel#MorningArt {
    font-size: 30px;
    font-weight: 900;
    color: #b96e3f;
}

QLabel#WeatherText {
    font-size: 25px;
    font-weight: 800;
    color: #263238;
}

QLabel#SectionSubtitle {
    font-size: 13px;
    font-weight: 800;
    color: #7b8b87;
    letter-spacing: 1px;
}

QLabel#SmallSectionTitle {
    font-size: 15px;
    font-weight: 900;
    color: #dbe8df;
    letter-spacing: 1px;
}

QLabel#StocksHeaderRight {
    font-size: 12px;
    font-weight: 900;
    color: #a9bbb4;
    letter-spacing: 1px;
}

QLabel#FoxHeadline {
    font-size: 29px;
    font-weight: 900;
    color: #9f4f45;
}

QLabel#CnbcHeadline {
    font-size: 27px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#LeagueTitle {
    font-size: 28px;
    font-weight: 900;
    color: #25313b;
}

QLabel#GameText {
    font-size: 28px;
    font-weight: 800;
    color: #33424b;
}

QLabel#AfterHoursLabel {
    font-size: 9px;
    font-weight: 900;
    color: #a9bbb4;
}

QLabel#ImageBadge {
    font-size: 17px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #b76e5f;
    border-radius: 8px;
    padding: 5px 10px;
}

QLabel#ImageBadgeBlue {
    font-size: 17px;
    font-weight: 900;
    color: #fff8ec;
    background-color: #4f7686;
    border-radius: 8px;
    padding: 5px 10px;
}

QLabel#ImageGraphicText {
    font-size: 24px;
    font-weight: 900;
    color: #536b6a;
}

QLabel#ImageGraphicTextDark {
    font-size: 24px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#SkyArt {
    font-size: 42px;
    font-weight: 900;
    color: #fff8ec;
}

QLabel#SkyArtLight {
    font-size: 42px;
    font-weight: 900;
    color: #7a938e;
}


QPushButton#DashboardSettingsButton {
    background-color: rgba(255, 250, 241, 175);
    color: #2f2a24;
    border: 1px solid rgba(117, 97, 72, 150);
    border-radius: 15px;
    font-size: 16px;
    font-weight: 900;
}

QPushButton#DashboardSettingsButton:hover {
    background-color: rgba(255, 250, 241, 230);
}

QPushButton#DashboardSettingsButton:pressed {
    background-color: rgba(222, 204, 168, 230);
}

QWidget#SettingsPage {
    background-color: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1f2d35,
        stop:0.45 #2f4548,
        stop:1 #5d6f63
    );
}

QFrame#SettingsCard {
    background-color: rgba(247, 241, 229, 245);
    border: 2px solid rgba(166, 149, 122, 180);
    border-radius: 18px;
}

QLabel#SettingsTitle {
    font-size: 34px;
    font-weight: 900;
    color: #2f2a24;
    letter-spacing: 2px;
}

QLabel#SettingsSubtitle {
    font-size: 14px;
    font-weight: 700;
    color: #5f5447;
}

QLabel#SettingsFieldLabel {
    font-size: 12px;
    font-weight: 900;
    color: #8b4e3f;
    letter-spacing: 2px;
}


QComboBox#SettingsComboBox {
    background-color: #f7f0df;
    color: #2d2114;
    border: 1px solid #b59b6c;
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 15px;
    font-weight: 900;
    selection-background-color: #d8c7a4;
    selection-color: #2d2114;
}

QComboBox#SettingsComboBox:hover {
    background-color: #fff7e8;
    border: 1px solid #8b6d3e;
}

QComboBox#SettingsComboBox:focus {
    background-color: #fff7e8;
    border: 2px solid #8b6d3e;
}

QComboBox#SettingsComboBox::drop-down {
    border: none;
    width: 34px;
    background-color: transparent;
}

QComboBox#SettingsComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox#SettingsComboBox QAbstractItemView {
    background-color: #f7f0df;
    color: #2d2114;
    border: 2px solid #8b6d3e;
    border-radius: 8px;
    padding: 6px;
    outline: none;
    selection-background-color: #8b5e2a;
    selection-color: #f7f0df;
    font-size: 15px;
    font-weight: 900;
}

QComboBox#SettingsComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 6px 10px;
    color: #2d2114;
    background-color: #f7f0df;
}

QComboBox#SettingsComboBox QAbstractItemView::item:hover {
    background-color: #eadab7;
    color: #2d2114;
}

QComboBox#SettingsComboBox QAbstractItemView::item:selected {
    background-color: #8b5e2a;
    color: #f7f0df;
}


QLineEdit#SettingsLineEdit {
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(110, 92, 62, 0.30);
    border-radius: 12px;
    padding: 9px 12px;
    color: #2d2a24;
    font-size: 15px;
    font-weight: 700;
}

QLineEdit#SettingsLineEdit:focus {
    border: 2px solid rgba(139, 109, 62, 0.72);
    background: rgba(255, 255, 255, 0.94);
}

# QLabel#DateLocationLabel {
#     color: #2d2a24;
#     background: transparent;
#     font-size: 12px;
#     font-weight: 900;
#     letter-spacing: 0.4px;
# }

QComboBox#SettingsComboBox::drop-down {
    border: none;
    width: 28px;
}

QComboBox#SettingsComboBox QAbstractItemView {
    background-color: #fffaf1;
    color: #2f2a24;
    selection-background-color: #d8c9ac;
    border: 1px solid rgba(117, 97, 72, 150);
    font-size: 15px;
}

QPushButton#SettingsPrimaryButton {
    background: rgba(114, 84, 45, 0.92);
    color: #f7f0df;
    border: 1px solid rgba(76, 55, 30, 0.45);
    border-radius: 12px;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 900;
}

QPushButton#SettingsPrimaryButton:hover {
    background: rgba(132, 98, 54, 0.96);
}

QPushButton#SettingsPrimaryButton:pressed {
    background: rgba(92, 67, 36, 0.98);
}

QPushButton#SettingsSecondaryButton {
    background: rgba(246, 238, 219, 0.88);
    color: #3a3124;
    border: 1px solid rgba(110, 92, 62, 0.35);
    border-radius: 12px;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 900;
}

QPushButton#SettingsSecondaryButton:hover {
    background: rgba(255, 247, 229, 0.96);
}

QPushButton#SettingsSecondaryButton:pressed {
    background: rgba(226, 214, 190, 0.96);
}

/* FINAL SETTINGS BUTTON OVERRIDE */
QPushButton#SettingsPrimaryButton {
    background-color: #72542d;
    color: #2d2114;
    border: 2px solid #4d351b;
    border-radius: 12px;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 900;
}

QPushButton#SettingsPrimaryButton:hover {
    background-color: #846236;
    color: #2d2114;
}

QPushButton#SettingsPrimaryButton:pressed {
    background-color: #5c4324;
    color: #f7f0df;
}

QPushButton#SettingsSecondaryButton {
    background-color: #d8c7a4;
    color: #2d2114;
    border: 2px solid #8b6d3e;
    border-radius: 12px;
    padding: 10px 18px;
    font-size: 15px;
    font-weight: 900;
}

QPushButton#SettingsSecondaryButton:hover {
    background-color: #eadab7;
    color: #2d2114;
}

QPushButton#SettingsSecondaryButton:pressed {
    background-color: #b79b6a;
    color: #2d2114;
}

/* STOCK SETTINGS SECTION */
QLabel#SettingsSectionTitle {
    color: #2d2114;
    background: transparent;
    font-size: 18px;
    font-weight: 1000;
    letter-spacing: 1.0px;
    margin-top: 8px;
}

QLabel#SettingsSectionSubtitle {
    color: rgba(45, 33, 20, 0.78);
    background: transparent;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 2px;
}

QWidget#StockSettingsRow {
    background: rgba(114, 84, 45, 0.14);
    border: 1px solid rgba(114, 84, 45, 0.22);
    border-radius: 10px;
}

QLabel#StockSettingsSlotLabel {
    color: #2d2114;
    background: transparent;
    font-size: 13px;
    font-weight: 1000;
    letter-spacing: 0.6px;
}

QLineEdit#StockSettingsLineEdit {
    background-color: #f7f0df;
    color: #2d2114;
    border: 1px solid #b59b6c;
    border-radius: 9px;
    padding: 7px 10px;
    font-size: 14px;
    font-weight: 900;
}

QLineEdit#StockSettingsLineEdit:focus {
    background-color: #fff7e8;
    border: 2px solid #8b6d3e;
}

/* APPLE CALENDAR SETTINGS */
QLabel#SettingsSectionTitle {
    color: #2d2114;
    background: transparent;
    font-size: 18px;
    font-weight: 1000;
    letter-spacing: 1.0px;
    margin-top: 8px;
}

QLabel#SettingsSectionSubtitle {
    color: rgba(45, 33, 20, 0.78);
    background: transparent;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 2px;
}



/* FAT NEWSPAPER TYPOGRAPHY PASS */

/* Mastheads */
QLabel#PaperMasthead,
QLabel#OldNewsTopMasthead,
QLabel#RemindersTitle {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 26px;
    font-weight: 1000;
    color: #241a10;
    background: transparent;
    border: none;
    letter-spacing: 1.8px;
}

/* Small edition/page labels */
QLabel#PaperEditionLine,
QLabel#PaperFooterPage,
QLabel#OldNewsEditionSmall,
QLabel#OldNewsPageNumber {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #5f4a30;
    background: transparent;
    border: none;
    letter-spacing: 1.1px;
}

/* Kicker labels */
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#OldNewsKicker,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #9c6424;
    background: transparent;
    border: none;
    letter-spacing: 1.3px;
}

/* Main article/news headlines */
QLabel#PaperHeadlineFeatured,
QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 23px;
    font-weight: 1000;
    color: #15100b;
    background: transparent;
    border: none;
}

/* Supporting headlines */
QLabel#PaperHeadline,
QLabel#Page2HeadlineText {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 13px;
    font-weight: 900;
    color: #20170f;
    background: transparent;
    border: none;
}

/* Game text */
QLabel#PaperGameMatchup,
QLabel#PaperLeagueTitle {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 16px;
    font-weight: 1000;
    color: #23190f;
    background: transparent;
    border: none;
}

QLabel#PaperGameTime,
QLabel#PaperGameDetail,
QLabel#PaperFooterLeft,
QLabel#OldNewsReadLink {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 900;
    color: #4f3d27;
    background: transparent;
    border: none;
}

/* Remove inner app-card/bubble feeling */
QWidget#PaperStory,
QWidget#PaperFeaturedStory,
QWidget#NewsPaperStoryPanel,
QWidget#Page2HeadlineBox {
    background: transparent;
    border: none;
    border-radius: 0px;
}

QWidget#NewsPaperPhotoBox {
    background-color: #d6c3a0;
    border: 1px solid rgba(48, 36, 22, 190);
    border-radius: 0px;
}

QWidget#TodayReminderRow {
    background-color: rgba(239, 213, 154, 0.72);
    border: 1px solid rgba(151, 111, 46, 145);
    border-radius: 0px;
}

QWidget#UpcomingReminderRow {
    background: transparent;
    border: none;
    border-top: 1px solid rgba(55, 42, 25, 110);
    border-radius: 0px;
}

QLabel#TodayReminderText {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 14px;
    font-weight: 1000;
    color: #1d150d;
}

QLabel#UpcomingReminderText {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 10px;
    font-weight: 800;
    color: #3f3020;
}

QPushButton#ReminderSendButton,
QPushButton#UpcomingReminderSendButton {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 1000;
    color: #2b1e10;
    background-color: #ead39a;
    border: 1px solid rgba(73, 53, 29, 170);
    border-radius: 0px;
    padding: 2px 8px;
}

QPushButton#ReminderSendButton:hover,
QPushButton#UpcomingReminderSendButton:hover {
    background-color: #f0ddb2;
}

/* END FAT NEWSPAPER TYPOGRAPHY PASS */


/* FOLDED BROADSHEET TUNING */

/* Main newspaper mastheads */
QLabel#PaperMasthead,
QLabel#OldNewsTopMasthead,
QLabel#RemindersTitle {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 25px;
    font-weight: 900;
    letter-spacing: 1px;
    color: #23180f;
    background: transparent;
    border: none;
}

/* Small labels / page numbers / business-politics tags */
QLabel#PaperEditionLine,
QLabel#PaperFooterPage,
QLabel#OldNewsEditionSmall,
QLabel#OldNewsPageNumber,
QLabel#PaperFooterLeft,
QLabel#OldNewsReadLink {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 900;
    letter-spacing: 1px;
    color: #5e4529;
    background: transparent;
    border: none;
}

/* Kicker lines */
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#OldNewsKicker,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 900;
    letter-spacing: 1.2px;
    color: #a3661e;
    background: transparent;
    border: none;
}

/* Main headlines */
QLabel#PaperHeadlineFeatured,
QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 22px;
    font-weight: 900;
    color: #17110b;
    background: transparent;
    border: none;
}

/* Secondary headlines */
QLabel#PaperHeadline,
QLabel#Page2HeadlineText {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 12px;
    font-weight: 800;
    color: #221811;
    background: transparent;
    border: none;
}

/* Game section labels */
QLabel#PaperGameMatchup,
QLabel#PaperLeagueTitle {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 16px;
    font-weight: 900;
    color: #241a11;
    background: transparent;
    border: none;
}

QLabel#PaperGameTime,
QLabel#PaperGameDetail {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 800;
    color: #4e3923;
    background: transparent;
    border: none;
}

/* Remove the app-card feeling inside newspaper panels */
QWidget#PaperStory,
QWidget#PaperFeaturedStory,
QWidget#NewsPaperStoryPanel,
QWidget#Page2HeadlineBox {
    background: transparent;
    border: none;
    border-radius: 0px;
}

/* News photo area still gets a printed frame */
QWidget#NewsPaperPhotoBox {
    background-color: rgba(213, 188, 145, 0.58);
    border: 1px solid rgba(73, 55, 29, 180);
    border-radius: 0px;
}

/* Reminder rows */
QWidget#TodayReminderRow {
    background-color: rgba(236, 210, 150, 0.48);
    border: 1px solid rgba(134, 101, 48, 120);
    border-radius: 0px;
}

QWidget#UpcomingReminderRow {
    background: transparent;
    border: none;
    border-top: 1px solid rgba(70, 52, 31, 85);
    border-radius: 0px;
}

QLabel#TodayReminderText {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 14px;
    font-weight: 900;
    color: #1d140d;
    background: transparent;
    border: none;
}

QLabel#UpcomingReminderText {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 10px;
    font-weight: 700;
    color: #423122;
    background: transparent;
    border: none;
}

QPushButton#ReminderSendButton,
QPushButton#UpcomingReminderSendButton {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 900;
    color: #2d1e10;
    background-color: rgba(245, 225, 181, 0.82);
    border: 1px solid rgba(76, 57, 31, 150);
    border-radius: 0px;
    padding: 2px 9px;
}

QPushButton#ReminderSendButton:hover,
QPushButton#UpcomingReminderSendButton:hover {
    background-color: rgba(249, 234, 198, 0.94);
}

/* END FOLDED BROADSHEET TUNING */


/* REFERENCE NEWSPAPER CARD STYLE */

/* Masthead like the reference */
QLabel#OldNewsTopMasthead,
QLabel#PaperMasthead,
QLabel#RemindersTitle {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 25px;
    font-weight: 1000;
    color: #241a10;
    background: transparent;
    border: none;
    letter-spacing: 2.4px;
}

/* The thin small right-side section/page text */
QLabel#OldNewsEditionSmall,
QLabel#PaperEditionLine,
QLabel#PaperFooterPage,
QLabel#OldNewsPageNumber,
QLabel#PaperFooterLeft {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #574128;
    background: transparent;
    border: none;
    letter-spacing: 1.2px;
}

/* Orange newspaper kicker */
QLabel#OldNewsKicker,
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #a05f18;
    background: transparent;
    border: none;
    letter-spacing: 1.4px;
}

/* Big article headline */
QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 31px;
    font-weight: 1000;
    color: #17100a;
    background: transparent;
    border: none;
    letter-spacing: -0.6px;
}

/* Sports lead headline */
QLabel#PaperHeadlineFeatured {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 22px;
    font-weight: 1000;
    color: #17100a;
    background: transparent;
    border: none;
}

/* Smaller newspaper headlines */
QLabel#PaperHeadline,
QLabel#Page2HeadlineText {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 12px;
    font-weight: 900;
    color: #22170f;
    background: transparent;
    border: none;
}

/* Read more footer */
QLabel#OldNewsReadLink {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 1000;
    color: #5a4024;
    background: transparent;
    border: none;
    letter-spacing: 1.1px;
}

/* Remove app-box feeling inside the article cards */
QWidget#NewsPaperStoryPanel,
QWidget#Page2Container,
QWidget#Page2HeadlineBox,
QWidget#PaperStory,
QWidget#PaperFeaturedStory {
    background: transparent;
    border: none;
    border-radius: 0px;
}

/* Image frame like a printed newspaper photo */
QWidget#NewsPaperPhotoBox {
    background-color: #d6c3a0;
    border: 1px solid rgba(43, 31, 16, 190);
    border-radius: 0px;
}

/* Reminders reference style */
QWidget#TodayReminderRow {
    background-color: rgba(237, 209, 143, 0.62);
    border: 1px solid rgba(135, 97, 39, 130);
    border-radius: 0px;
}

QWidget#UpcomingReminderRow {
    background: transparent;
    border: none;
    border-top: 1px solid rgba(73, 53, 29, 90);
    border-radius: 0px;
}

QLabel#TodayReminderText {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 15px;
    font-weight: 1000;
    color: #1d140c;
    background: transparent;
    border: none;
}

QLabel#UpcomingReminderText {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 10px;
    font-weight: 800;
    color: #40301f;
    background: transparent;
    border: none;
}

QPushButton#ReminderSendButton,
QPushButton#UpcomingReminderSendButton {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 1000;
    color: #2d1e10;
    background-color: rgba(245, 225, 181, 0.88);
    border: 1px solid rgba(76, 57, 31, 160);
    border-radius: 0px;
    padding: 2px 10px;
}

QPushButton#ReminderSendButton:hover,
QPushButton#UpcomingReminderSendButton:hover {
    background-color: rgba(249, 234, 198, 0.96);
}

/* END REFERENCE NEWSPAPER CARD STYLE */



/* NEWSPAPER TITLE FONT REFINEMENT */

/* Big newspaper section mastheads: BUSINESS, HEADLINES, REMINDERS */
QLabel#OldNewsTopMasthead,
QLabel#RemindersTitle {
    font-family: "Bodoni 72 Smallcaps", "Bodoni 72", "Georgia", "Times New Roman", serif;
    font-size: 31px;
    font-weight: 1000;
    color: #24170c;
    background: transparent;
    border: none;
    letter-spacing: 3px;
}

/* Sports/Game Times mastheads if any QLabel versions still exist */
QLabel#PaperMasthead {
    font-family: "Bodoni 72 Smallcaps", "Bodoni 72", "Georgia", "Times New Roman", serif;
    font-size: 30px;
    font-weight: 1000;
    color: #24170c;
    background: transparent;
    border: none;
    letter-spacing: 2.6px;
}

/* Small top-right tags like P. 1, BUSINESS, POLITICS */
QLabel#OldNewsEditionSmall,
QLabel#PaperEditionLine,
QLabel#PaperFooterPage,
QLabel#OldNewsPageNumber {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #5a3f22;
    background: transparent;
    border: none;
    letter-spacing: 1.4px;
}

/* Reference-style orange section kicker */
QLabel#OldNewsKicker,
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #a05f18;
    background: transparent;
    border: none;
    letter-spacing: 1.4px;
}

/* Large article headline closer to reference */
QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 30px;
    font-weight: 1000;
    color: #15100a;
    background: transparent;
    border: none;
    letter-spacing: -0.7px;
}

/* END NEWSPAPER TITLE FONT REFINEMENT */


/* NEWSPAPER_SHAPE_STYLE_START */

/* shared newspaper section shells */
QWidget#NewspaperSportsCard,
QWidget#PaperGameTimesPanel,
QWidget#OldNewsCard,
QWidget#RemindersPanel {
    background: transparent;
    border: none;
}

/* strong old-paper mastheads */
QLabel#PaperMasthead,
QLabel#OldNewsTopMasthead,
QLabel#RemindersTitle {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 29px;
    font-weight: 900;
    color: #2b1a0f;
    background: transparent;
    border: none;
    letter-spacing: 1px;
}

/* section micros / page numbers */
QLabel#PaperEditionLine,
QLabel#OldNewsEditionSmall,
QLabel#OldNewsPageNumber,
QLabel#PaperFooterPage,
QLabel#PaperFooterLeft {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 700;
    color: #6b4d2a;
    background: transparent;
    border: none;
    letter-spacing: 1px;
}

/* orange kicker text */
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#OldNewsKicker,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 800;
    color: #b06a1b;
    background: transparent;
    border: none;
    letter-spacing: 1px;
}

/* sports lead */
QLabel#PaperHeadlineFeatured {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 24px;
    font-weight: 900;
    color: #1b120c;
    background: transparent;
    border: none;
}

/* article headlines */
QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 27px;
    font-weight: 900;
    color: #1a110b;
    background: transparent;
    border: none;
}

/* body / lower story text */
QLabel#PaperHeadline,
QLabel#OldNewsSubheadline,
QLabel#OldNewsSummary,
QLabel#ReminderPrimaryText,
QLabel#ReminderSecondaryText {
    font-family: "Georgia", "Times New Roman", serif;
    color: #2a1c12;
    background: transparent;
    border: none;
}

/* inner story boxes should stop looking like app cards */
QWidget#PaperStory,
QWidget#PaperFeaturedStory,
QWidget#NewsPaperStoryPanel,
QWidget#Page2Container,
QWidget#Page2HeadlineBox {
    background: transparent;
    border: none;
    border-radius: 0px;
}

/* image frame */
QWidget#NewsPaperPhotoBox {
    background-color: rgba(218, 195, 157, 0.65);
    border: 1px solid rgba(79, 56, 31, 145);
    border-radius: 0px;
}

/* reminder rows */
QWidget#TodayReminderRow {
    background-color: rgba(235, 208, 149, 0.45);
    border: 1px solid rgba(138, 101, 48, 110);
    border-radius: 0px;
}

QWidget#UpcomingReminderRow {
    background: transparent;
    border: none;
    border-top: 1px solid rgba(97, 70, 36, 90);
    border-radius: 0px;
}

/* reminder buttons */
QPushButton#ReminderSendButton,
QPushButton#UpcomingReminderSendButton {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 800;
    color: #2b1a10;
    background-color: rgba(244, 227, 190, 0.9);
    border: 1px solid rgba(88, 65, 39, 145);
    border-radius: 2px;
    padding: 3px 10px;
}

/* NEWSPAPER_SHAPE_STYLE_END */



/* OLD TOWN NEWSPAPER FONT PASS */

/* Old-town mastheads: strong but not colliding with borders */
QLabel#OldNewsTopMasthead,
QLabel#PaperMasthead,
QLabel#RemindersTitle {
    font-family: "Rockwell", "Georgia", "Times New Roman", serif;
    font-size: 27px;
    font-weight: 1000;
    color: #2b1a0f;
    background: transparent;
    border: none;
    letter-spacing: 1.2px;
}

/* Page numbers and section markers */
QLabel#OldNewsEditionSmall,
QLabel#OldNewsPageNumber,
QLabel#PaperEditionLine,
QLabel#PaperFooterPage,
QLabel#PaperFooterLeft {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #684a27;
    background: transparent;
    border: none;
    letter-spacing: 1px;
}

/* Orange/brown newspaper kicker */
QLabel#OldNewsKicker,
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #9b5914;
    background: transparent;
    border: none;
    letter-spacing: 1.2px;
}

/* Lead story headline */
QLabel#OldNewsHeadline {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 27px;
    font-weight: 1000;
    color: #170f08;
    background: transparent;
    border: none;
    letter-spacing: -0.4px;
}

/* Sports lead headline */
QLabel#PaperHeadlineFeatured {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 22px;
    font-weight: 1000;
    color: #170f08;
    background: transparent;
    border: none;
}

/* Remove digital box feel */
QWidget#NewsPaperStoryPanel,
QWidget#Page2Container,
QWidget#Page2HeadlineBox,
QWidget#PaperStory,
QWidget#PaperFeaturedStory {
    background: transparent;
    border: none;
    border-radius: 0px;
}

/* Printed photo frame */
QWidget#NewsPaperPhotoBox {
    background-color: #d7c098;
    border: 1px solid rgba(58, 38, 18, 175);
    border-radius: 0px;
}

/* Reminder rows */
QWidget#TodayReminderRow {
    background-color: rgba(234, 204, 136, 0.62);
    border: 1px solid rgba(120, 82, 34, 130);
    border-radius: 0px;
}

QWidget#UpcomingReminderRow {
    background: transparent;
    border: none;
    border-top: 1px solid rgba(73, 49, 23, 90);
    border-radius: 0px;
}

QPushButton#ReminderSendButton,
QPushButton#UpcomingReminderSendButton {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 9px;
    font-weight: 1000;
    color: #28190d;
    background-color: rgba(238, 215, 171, 0.9);
    border: 1px solid rgba(76, 52, 27, 155);
    border-radius: 0px;
    padding: 2px 10px;
}

/* END OLD TOWN NEWSPAPER FONT PASS */



/* MATCH NEWS REMINDER HEADERS TO SPORTS FONT */
QLabel#OldNewsTopMasthead,
QLabel#RemindersTitle {
    font-family: "Rockwell", "Georgia", "Times New Roman", serif;
    font-size: 25px;
    font-weight: 1000;
    color: #2b1a0f;
    background: transparent;
    border: none;
    letter-spacing: 1.4px;
}
/* END MATCH NEWS REMINDER HEADERS TO SPORTS FONT */






/* MATCH NEWS HEADERS TO SPORTS MASTHEAD */

/* Make BUSINESS, HEADLINES, and REMINDERS use the same family/style as GAME TIMES and SPORTS DESK */
QLabel#OldNewsTopMasthead,
QLabel#RemindersTitle,
QLabel#PaperMasthead {
    font-family: "Rockwell", "Georgia", "Times New Roman", serif;
    font-size: 25px;
    font-weight: 1000;
    color: #2b1a0f;
    background: transparent;
    border: none;
    letter-spacing: 1.4px;
}

/* Keep the little right-side labels small like a newspaper page marker */
QLabel#OldNewsEditionSmall,
QLabel#OldNewsPageNumber,
QLabel#PaperEditionLine,
QLabel#PaperFooterPage,
QLabel#PaperFooterLeft {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #684a27;
    background: transparent;
    border: none;
    letter-spacing: 1px;
}

/* Kicker labels */
QLabel#OldNewsKicker,
QLabel#PaperKicker,
QLabel#PaperKickerFeatured,
QLabel#TodayReminderGroupTitle,
QLabel#UpcomingReminderGroupTitle {
    font-family: "Times New Roman", "Georgia", serif;
    font-size: 8px;
    font-weight: 1000;
    color: #9b5914;
    background: transparent;
    border: none;
    letter-spacing: 1.2px;
}

/* END MATCH NEWS HEADERS TO SPORTS MASTHEAD */

"""
