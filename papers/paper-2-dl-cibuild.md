# Reading Notes - Improving the Prediction of Continuous Integration Build Failures Using Deep Learning

## Identitas Paper

Judul: Improving the Prediction of Continuous Integration Build Failures Using Deep Learning

Penulis: Islem Saidani, Ali Ouni, Mohamed Wiem Mkaouer

Tahun dan venue: 2022, Automated Software Engineering, Springer

Topik utama: prediksi build failure CI menggunakan LSTM-based recurrent neural networks.

## Klaim Utama

Paper ini mengklaim bahwa histori build CI mengandung pola temporal yang dapat dipelajari untuk memprediksi build failure. Penulis memperkenalkan DL-CIBuild, pendekatan berbasis LSTM-RNN untuk memprediksi outcome build dari urutan build sebelumnya. Paper juga memakai Genetic Algorithm untuk hyperparameter optimization dan threshold moving untuk menangani imbalance antara passed builds dan failed builds.

Klaim ini relevan untuk TaskFlow karena menunjukkan bahwa data historis CI/CD bukan hanya arsip pasif. Data historis bisa menjadi input sistem intelligence yang membantu developer mendapat feedback lebih cepat. Namun TaskFlow tidak mereplikasi model LSTM karena ukuran dataset kecil dan scope final project terbatas.

## Metodologi Paper

Penulis memformulasikan CI build failure prediction sebagai masalah time series. Input model adalah urutan hasil build sebelumnya, bukan feature engineering manual yang kompleks. Model LSTM digunakan karena mampu menangkap dependensi jangka pendek dan jangka panjang dalam data sekuensial.

Evaluasi dilakukan pada benchmark 91.330 CI builds dari 10 proyek open source yang menggunakan Travis CI. Paper membandingkan DL-CIBuild dengan beberapa baseline machine learning seperti Random Forest, Decision Tree, AdaBoost, Logistic Regression, dan Support Vector Classification. Paper juga mengevaluasi beberapa skenario seperti online validation, cross-project validation, sensitivity terhadap ukuran training data, dan robustness terhadap concept drift.

Metrik evaluasi yang digunakan antara lain AUC, F1-score, accuracy, dan computational time. Paper melaporkan bahwa LSTM-based model mengungguli model ML tradisional pada skenario online dan cross-project validation. Untuk cross-project validation, paper melaporkan median AUC 72 persen, F1-score 57 persen, dan accuracy 78 persen.

## Temuan Kunci

Temuan pertama adalah bahwa build outcome history dapat dipakai untuk membangun automation yang lebih cerdas dalam CI. Ini memperkuat argumen bahwa pipeline tidak harus berhenti pada status binary sukses atau gagal.

Temuan kedua adalah bahwa failed builds sering lebih penting daripada passed builds, tetapi jumlahnya lebih sedikit. Ini menciptakan data imbalance. Untuk TaskFlow, masalah yang mirip muncul pada knowledge base: real failed logs sedikit, sehingga synthetic validated logs dipakai untuk mengurangi cold-start.

Temuan ketiga adalah bahwa model yang terlalu ambisius membutuhkan dataset besar, training, dan tuning. Paper menggunakan 91.330 build records, sedangkan TaskFlow tidak memiliki histori sebesar itu. Karena itu implementasi TaskFlow tidak memilih training LSTM, tetapi mengambil ide umum: gunakan histori CI sebagai feedback intelligence.

## Relevansi Langsung untuk Implementasi TaskFlow

Paper ini menjadi landasan bahwa historical CI data dapat dimanfaatkan untuk automation berbasis AI. TaskFlow menerapkan versi yang lebih realistis untuk scope satu minggu:

- Bukan build outcome prediction.
- Bukan training LSTM.
- Fokus pada failure similarity retrieval dan LLM explanation.
- Knowledge base dibuat dari synthetic validated logs dan nantinya real failed GitHub Actions logs.

Keputusan ini menjaga implementasi tetap feasible, reproducible, dan langsung terintegrasi ke pipeline yang sudah ada.

## Keterbatasan Paper

Paper menggunakan Travis CI, bukan GitHub Actions. Dataset paper juga jauh lebih besar daripada TaskFlow. DL-CIBuild membutuhkan training, hyperparameter optimization, dan pengelolaan concept drift. Untuk proyek mahasiswa satu minggu, biaya implementasi ini tidak sebanding dengan manfaat langsung.

Paper juga berfokus pada prediksi apakah build berikutnya akan gagal, sedangkan kebutuhan TaskFlow adalah membantu developer memahami failure setelah pipeline gagal. Dengan kata lain, problem TaskFlow adalah diagnosis assistance, bukan preemptive prediction.

## Hal yang Diragukan atau Perlu Dikritisi

Pertanyaan utama adalah apakah build outcome sequence saja cukup untuk menjelaskan root cause. Prediksi failure bisa memberi peringatan, tetapi developer tetap membutuhkan evidence log dan debugging steps. Karena itu TaskFlow memilih kombinasi retrieval dan LLM report. Pendekatan ini lebih langsung membantu saat failure terjadi.

## Implikasi untuk Evaluasi Proyek

Paper ini mendorong evaluasi yang tidak hanya melihat akurasi teknis, tetapi juga usefulness bagi workflow developer. Untuk TaskFlow, metrik yang relevan adalah:

- Waktu dari pipeline failure ke diagnosis awal.
- Apakah report mengurangi kebutuhan membaca raw log.
- Apakah top-k similar failures memberi hint yang benar.
- Apakah sistem tetap robust saat API key tidak tersedia.

Paper ini juga menjadi argumen mengapa TaskFlow tidak melakukan training model sendiri: dataset kecil, cost tinggi, dan tujuan proyek berbeda.

