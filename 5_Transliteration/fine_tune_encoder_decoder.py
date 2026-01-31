from transformers import RobertaTokenizer, XLMRobertaTokenizer

encoder_tokenizer = XLMRobertaTokenizer.from_pretrained("xlm-roberta-base")
decoder_tokenizer = RobertaTokenizer.from_pretrained("roberta-base")


def preprocess_function(examples):
    encoder_inputs = encoder_tokenizer(
        examples["source"], truncation=True, padding="max_length", max_length=128
    )
    with encoder_tokenizer.as_target_tokenizer():
        labels = decoder_tokenizer(
            examples["target"], truncation=True, padding="max_length", max_length=128
        )
    encoder_inputs["labels"] = labels["input_ids"]
    return encoder_inputs


tokenized_datasets = dataset.map(preprocess_function, batched=True)

# This is a simplified example. Actual implementation would require ensuring compatibility between encoder and decoder models.
from transformers import EncoderDecoderModel, RobertaModel, XLMRobertaModel

# Load pre-trained models
encoder = XLMRobertaModel.from_pretrained("xlm-roberta-base")
decoder = RobertaModel.from_pretrained("roberta-base")

# Combine them into an encoder-decoder model
model = EncoderDecoderModel(encoder=encoder, decoder=decoder)

from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

training_args = Seq2SeqTrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=4,
    weight_decay=0.01,
    save_total_limit=3,
    num_train_epochs=3,
    predict_with_generate=True,
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    # Implement compute_metrics function to calculate BLEU score
)

from datasets import load_metric

bleu_metric = load_metric("sacrebleu")


def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    decoded_preds = decoder_tokenizer.batch_decode(
        predictions, skip_special_tokens=True
    )
    # Replace -100 in the labels as we can't decode them.
    labels = np.where(labels != -100, labels, decoder_tokenizer.pad_token_id)
    decoded_labels = decoder_tokenizer.batch_decode(labels, skip_special_tokens=True)

    # Compute BLEU score
    result = bleu_metric.compute(predictions=decoded_preds, references=decoded_labels)
    return {"bleu": result["score"]}


trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    compute_metrics=compute_metrics,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
)
